import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { onAccountReset, type AccountKey } from '../../components/account';
import { ApiError } from '../../components/api';
import { useAuth } from '../../components/auth';
import { uid } from '../../lib/common';
import { useConsultThreads } from '../consult/useConsultThreads';
import { SAMPLE_AFTERCARE } from './sampleAftercare';
import { displayStatus } from '../consult/types';
import { getAftercare, listAftercare, PHOTO_ONLY, sendAftercare, toLocalMessage, uploadAftercare, type ServerThread } from './aftercareApi';
import type { AftercareMessage, Attachment } from './types';

// 사후 관리 대상 = 방문 완료로 보이는 예약만 (확정 + 방문 일시 지남, 예약 내역 기반)
// 저장: demo는 예시로 시작해 메모리에만, member는 서버(/me/aftercare, contracts 6-3). 사진·영상 미리보기는 이 탭 메모리에만
type Mode = 'demo' | 'member';
type Store = Record<string, { messages: AftercareMessage[]; unread: number }>;
// 메모리는 계정별로 나누고, 로그아웃·탈퇴하면 모두 지운다
const memory = new Map<AccountKey, Store>();
onAccountReset(() => {
  // 보낸 사진·영상의 임시 주소(blob:)도 풀어 준다
  memory.forEach((store) =>
    Object.values(store).forEach((v) =>
      v.messages.forEach((m) => m.attachments?.forEach((a) => a.url.startsWith('blob:') && URL.revokeObjectURL(a.url))),
    ),
  );
  memory.clear();
});
const load = (key: AccountKey, mode: Mode): Store => {
  if (!memory.has(key)) memory.set(key, mode === 'demo' ? SAMPLE_AFTERCARE : {});
  return memory.get(key)!;
};


// 서버 메시지 (사진·영상은 서버의 서명된 주소). 저장소가 꺼진 서버라 주소가 없으면 이 탭에서 보낸 미리보기로
const withFiles = (t: ServerThread, files: Map<string, Attachment[]>): AftercareMessage[] =>
  (t.messages ?? []).map((m) => {
    const local = toLocalMessage(m);
    const att = files.get(local.id);
    return !local.attachments && att ? { ...local, text: local.text === PHOTO_ONLY ? undefined : local.text, attachments: att } : local;
  });
const sentFiles = new Map<string, Attachment[]>(); // 서버 메시지 id → 첨부 (계정 초기화 때 위에서 같이 풀림)
onAccountReset(() => sentFiles.clear());

export type AftercareError = 'closed' | 'failed' | null;

export function useAftercare() {
  const { user, account, token } = useAuth();
  const mode: Mode = user?.demo ? 'demo' : 'member';
  const consult = useConsultThreads();
  const [store, setStore] = useState<Store>(() => load(account, mode));
  const [activeId, setActiveId] = useState<string | null>(null);
  const [error, setError] = useState<AftercareError>(null);
  const accountRef = useRef(account);
  accountRef.current = account;

  useEffect(() => {
    setStore(load(account, mode));
    setActiveId(null);
  }, [account, mode]);

  const update = useCallback((fn: (prev: Store) => Store) => {
    const key = accountRef.current; // 계정이 바뀐 뒤의 늦은 변경이 다른 계정 메모리에 들어가지 않게
    setStore((prev) => {
      const next = fn(prev);
      memory.set(key, next);
      return next;
    });
  }, []);

  // 실제 회원: 방문 완료 예약의 서버 대화를 불러옴 (요청서 id = booking.serverId)
  const visitedIds = consult.bookings
    .filter((b) => displayStatus(b.booking) === 'visited' && b.booking.serverId)
    .map((b) => `${b.message.id}:${b.booking.serverId}`)
    .join(',');
  useEffect(() => {
    if (mode !== 'member' || !token || !visitedIds) return;
    const key = account;
    let alive = true;
    (async () => {
      const byServer = new Map(visitedIds.split(',').map((p) => p.split(':') as [string, string]).map(([local, server]) => [server, local]));
      const list = (await listAftercare(token)).filter((t) => byServer.has(t.request_id));
      const full = await Promise.all(list.map(async (t) => ({ ...(await getAftercare(token, t.request_id)), unread: t.unread })));
      if (!alive || accountRef.current !== key) return;
      update((prev) => {
        const next = { ...prev };
        for (const t of full) {
          const id = byServer.get(t.request_id)!;
          next[id] = { messages: withFiles(t, sentFiles), unread: t.unread };
        }
        return next;
      });
    })().catch(() => {
      /* 서버 연결 실패: 이 탭의 기록만 보여 줌 */
    });
    return () => {
      alive = false;
    };
  }, [mode, token, account, visitedIds, update]);

  // 방문일이 최근인 순
  const visits = useMemo(
    () =>
      consult.bookings
        .filter((b) => displayStatus(b.booking) === 'visited') // 병원이 방문 완료 표시한 예약 (데모 계정은 확정 + 방문 일시 지남, consult/types.ts)
        .map((b) => ({ id: b.message.id, thread: b.thread, booking: b.booking, ...(store[b.message.id] ?? { messages: [], unread: 0 }) }))
        .sort((a, b) => `${b.booking.date}T${b.booking.time}`.localeCompare(`${a.booking.date}T${a.booking.time}`)),
    [consult.bookings, store],
  );
  const active = visits.find((v) => v.id === activeId) ?? visits[0] ?? null;

  const select = (id: string) => {
    setActiveId(id);
    setError(null);
    update((prev) => (prev[id]?.unread ? { ...prev, [id]: { ...prev[id], unread: 0 } } : prev));
  };

  const send = async (text: string, attachments: Attachment[]) => {
    if (!active || (!text.trim() && !attachments.length)) return false;
    setError(null);
    const msg: AftercareMessage = { id: uid(), from: 'user', at: new Date().toISOString(), text: text.trim() || undefined, attachments: attachments.length ? attachments : undefined };
    const serverId = active.booking.serverId;
    if (mode === 'member' && token && serverId) {
      const key = accountRef.current;
      try {
        const uploaded = await Promise.all(attachments.map((a) => uploadAftercare(token, serverId, a)));
        const stored = uploaded.filter((u) => u !== null);
        const t = await sendAftercare(token, serverId, text.trim(), attachments.length > 0, stored);
        const mine = (t.messages ?? []).filter((m) => m.sender === 'patient');
        // 저장소에 못 올린 것(꺼진 서버)만 이 탭 미리보기로 남김
        if (attachments.length && !stored.length && mine.length) sentFiles.set(`srv-${mine[mine.length - 1].id}`, attachments);
        if (stored.length) attachments.forEach((a) => a.url.startsWith('blob:') && URL.revokeObjectURL(a.url)); // 서버 주소로 보여 주므로 미리보기는 풀어 줌
        if (accountRef.current !== key) return false;
        update((prev) => ({ ...prev, [active.id]: { messages: withFiles(t, sentFiles), unread: 0 } }));
        return true;
      } catch (e) {
        // 실패하면 쓴 글·첨부는 입력창에 그대로 둠. 409 = 방문 완료 전이거나 사후관리를 지원하지 않는 병원 → 병원에 직접 연락 안내
        setError(e instanceof ApiError && e.status === 409 ? 'closed' : 'failed');
        return false;
      }
    }
    update((prev) => {
      const cur = prev[active.id] ?? { messages: [], unread: 0 };
      return { ...prev, [active.id]: { ...cur, messages: [...cur.messages, msg] } };
    });
    return true;
  };

  return { mode, visits, active, select, send, error };
}
