import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { onAccountReset, type AccountKey } from '../../components/account';
import { useAuth } from '../../components/auth';
import { searchText, uid } from '../../lib/common';
import { useHospitals } from '../hospital/useHospitals';
import { hospitalNames } from '../hospital/name';
import { cancelMine, createBooking, listMine, toLocal, ykihoOf, type BookingExtra } from './bookingApi';
import { SAMPLE_THREADS } from './sampleThreads';
import type { BookingRequest, ConsultThread } from './types';

// 저장 방식
// - demo: 예시 상담으로 시작, 바꾼 내용은 메모리에만
// - member: 예약 요청·취소는 서버(/hospitals/{id}/booking-requests, /me/booking-requests), 상담 글은 아직 메모리 (상담 답장 API는 B)
// 메모리는 계정별로 나누고, 로그아웃·탈퇴하면 모두 지운다 (같은 탭의 다음 사용자에게 보이지 않게)
// 병원 답변은 병원 담당자가 직접 쓴다. 이 화면은 답을 지어내지 않는다
type Mode = 'demo' | 'member';
const memory = new Map<AccountKey, ConsultThread[]>();
onAccountReset(() => memory.clear());

const load = (key: AccountKey, mode: Mode) => {
  if (!memory.has(key)) memory.set(key, mode === 'demo' ? SAMPLE_THREADS : []);
  return memory.get(key)!;
};
const save = (key: AccountKey, list: ConsultThread[]) => {
  memory.set(key, list);
  // TODO(member): 상담 백엔드가 생기면 여기서 서버에 저장
};

const lastAt = (t: ConsultThread) => t.messages[t.messages.length - 1]?.at ?? '';

type NewThread = Omit<ConsultThread, 'messages' | 'unread'>;

// 서버 답장을 상담 메시지로 붙일 때 쓰는 id (같은 답장이 두 번 붙지 않게)
const replyId = (requestId: string, sentAt: string) => `reply-${requestId}-${sentAt}`;

export function useConsultThreads() {
  const { user, account, token } = useAuth();
  const mode: Mode = user?.demo ? 'demo' : 'member';
  const hospitals = useHospitals();
  const [list, setList] = useState<ConsultThread[]>(() => load(account, mode));
  const [activeId, setActiveId] = useState<string | null>(null);
  const accountRef = useRef(account);
  accountRef.current = account;

  useEffect(() => {
    setList(load(account, mode));
    setActiveId(null);
  }, [account, mode]);

  // 실제 회원: 서버의 내 예약 요청으로 상담·예약 상태를 맞춤 (새로 고침해도 남고, 병원이 확정하면 "확정"으로 바뀜)
  useEffect(() => {
    if (mode !== 'member' || !token || hospitals.status !== 'ready') return;
    const key = account;
    let alive = true;
    (async () => {
      const mine = await listMine(token);
      const rows = await Promise.all(mine.map(async (s) => ({ s, ykiho: await ykihoOf(s.hospital_id) })));
      if (!alive || accountRef.current !== key) return;
      const byId = new Map(hospitals.data.items.map((h) => [h.id, h]));
      setList((prev) => {
        let next = prev;
        for (const { s, ykiho } of rows) {
          const h = ykiho ? byId.get(ykiho) : undefined;
          if (!ykiho || !h) continue;
          const local = toLocal(s);
          if (!next.some((t) => t.hospitalId === ykiho)) {
            next = [{ hospitalId: ykiho, name: hospitalNames(h), dept: h.depts[0], district: h.district, photo: h.photo, messages: [], unread: 0 }, ...next];
          }
          next = next.map((t) => {
            if (t.hospitalId !== ykiho) return t;
            const has = t.messages.some((m) => m.booking?.serverId === s.id);
            let messages = has
              ? t.messages.map((m) => (m.booking?.serverId === s.id ? { ...m, booking: { ...m.booking, ...local } } : m))
              : [...t.messages, { id: uid(), from: 'user' as const, at: s.created_at, booking: local }];
            // 병원 답장 (서버 저장). 아직 없던 것만 붙이고 안 읽은 수에 더함. 번역 전이면 한국어 원문
            const fresh = (s.replies ?? []).filter((r) => !messages.some((m) => m.id === replyId(s.id, r.sent_at)));
            messages = [
              ...messages,
              ...fresh.map((r) => ({ id: replyId(s.id, r.sent_at), from: 'staff' as const, at: r.sent_at, text: r.text_translated || r.text_ko })),
            ].sort((a, b) => Date.parse(a.at) - Date.parse(b.at));
            return { ...t, messages, unread: t.unread + fresh.length };
          });
        }
        save(key, next);
        return next;
      });
    })().catch(() => {
      /* 서버 연결 실패: 이 탭의 기록만 보여 줌 */
    });
    return () => {
      alive = false;
    };
  }, [mode, token, account, hospitals.status]);

  // 지금 계정의 메모리에만 저장 (계정이 바뀐 뒤 늦게 도착한 변경은 버림)
  const update = useCallback((fn: (prev: ConsultThread[]) => ConsultThread[]) => {
    const key = accountRef.current;
    setList((prev) => {
      const next = fn(prev);
      save(key, next);
      return next;
    });
  }, []);

  // 최근 대화가 있는 병원이 위로 (메시지가 없는 새 상담은 맨 위)
  const threads = useMemo(
    () => [...list].sort((a, b) => (Date.parse(lastAt(b)) || Infinity) - (Date.parse(lastAt(a)) || Infinity)),
    [list],
  );
  const active = threads.find((t) => t.hospitalId === activeId) ?? threads[0] ?? null;

  // 상담을 열면 병원 답변을 읽은 것으로 처리
  const select = (id: string) => {
    setActiveId(id);
    update((prev) => prev.map((t) => (t.hospitalId === id && t.unread ? { ...t, unread: 0 } : t)));
  };

  // 같은 병원 상담이 이미 있으면 그 상담을 연다 (병원당 하나)
  const open = (thread: NewThread) => {
    update((prev) => (prev.some((t) => t.hospitalId === thread.hospitalId) ? prev : [{ ...thread, messages: [], unread: 0 }, ...prev]));
    setActiveId(thread.hospitalId);
  };

  const append = (id: string, msg: { text?: string; booking?: BookingRequest }) =>
    update((prev) =>
      prev.map((t) =>
        t.hospitalId === id ? { ...t, messages: [...t.messages, { id: uid(), from: 'user', at: new Date().toISOString(), ...msg }] } : t,
      ),
    );

  const editBooking = (id: string, messageId: string, fn: (b: BookingRequest) => BookingRequest) =>
    update((prev) =>
      prev.map((t) =>
        t.hospitalId === id ? { ...t, messages: t.messages.map((m) => (m.id === messageId && m.booking ? { ...m, booking: fn(m.booking) } : m)) } : t,
      ),
    );

  const bookingOf = (id: string, messageId: string) =>
    list.find((t) => t.hospitalId === id)?.messages.find((m) => m.id === messageId)?.booking;

  // 변경하면 병원이 다시 확인해야 하므로 확인 대기로 돌아간다 (예약번호도 새로 받음)
  // 실제 회원: 서버에는 "변경"이 없어서 기존 요청을 취소하고 새로 요청한다 (contracts 6-1절)
  const changeBooking = async (id: string, messageId: string, b: Omit<BookingRequest, 'status'>, notice: string, extra?: BookingExtra) => {
    const thread = list.find((t) => t.hospitalId === id);
    const old = bookingOf(id, messageId);
    if (mode === 'member' && token && thread) {
      if (old?.serverId) await cancelMine(token, old.serverId);
      const next = await toServer(thread, b, extra);
      editBooking(id, messageId, () => next);
    } else {
      editBooking(id, messageId, (o) => ({ ...o, ...b, status: 'pending', bookingNo: undefined }));
    }
    append(id, { text: notice });
  };

  const cancelBooking = async (id: string, messageId: string, notice: string) => {
    const old = bookingOf(id, messageId);
    if (mode === 'member' && token && old?.serverId) await cancelMine(token, old.serverId);
    editBooking(id, messageId, (o) => ({ ...o, status: 'cancelled', cancelledAt: new Date().toISOString() }));
    append(id, { text: notice });
  };

  const send = (text: string) => active && text.trim() && append(active.hospitalId, { text: text.trim() });

  // 실제 회원은 서버에 예약 요청을 보내고(실패하면 거부된 Promise → 폼이 오류 표시), 서버가 준 상태로 남긴다
  const toServer = async (thread: NewThread, b: Omit<BookingRequest, 'status'>, extra?: BookingExtra): Promise<BookingRequest> => {
    if (mode === 'demo' || !token) return { ...b, status: 'pending' };
    if (!extra) throw new Error('consent');
    return (await createBooking(token, thread.hospitalId, thread.dept, b, extra)).local;
  };

  const requestBooking = async (b: Omit<BookingRequest, 'status'>, extra?: BookingExtra) => {
    if (!active) return;
    const booking = await toServer(active, b, extra);
    append(active.hospitalId, { booking });
  };

  // 병원 목록의 "예약하기"에서 신청: 그 병원 상담이 없으면 만들고, 상담에 예약 요청을 남긴다 (확정은 병원이 한다)
  const requestBookingFor = async (thread: NewThread, b: Omit<BookingRequest, 'status'>, extra?: BookingExtra) => {
    const booking = await toServer(thread, b, extra);
    update((prev) => {
      const list = prev.some((t) => t.hospitalId === thread.hospitalId) ? prev : [{ ...thread, messages: [], unread: 0 }, ...prev];
      const msg = { id: uid(), from: 'user' as const, at: new Date().toISOString(), booking };
      return list.map((t) => (t.hospitalId === thread.hospitalId ? { ...t, messages: [...t.messages, msg] } : t));
    });
  };

  const search = (q: string) => {
    const s = q.trim().toLowerCase();
    if (!s) return threads;
    return threads.filter((t) => searchText(t.name).toLowerCase().includes(s) || t.messages.some((m) => searchText(m.text).toLowerCase().includes(s)));
  };

  const bookings = threads.flatMap((t) => t.messages.filter((m) => m.booking).map((m) => ({ thread: t, message: m, booking: m.booking! })));

  return { mode, threads, active, select, open, send, requestBooking, requestBookingFor, changeBooking, cancelBooking, search, bookings };
}
