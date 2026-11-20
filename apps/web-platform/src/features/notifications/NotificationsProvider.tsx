// 사이트 안 알림: 병원이 예약 상태를 바꾸거나(확정·거절·시간 제안·방문 완료·미방문·기간 지남) 답장을 보냈을 때
// 서버에 알림 표는 없음 → 내 예약·사후관리를 주기적으로 불러, 이 브라우저에 저장한 "마지막으로 본 상태"와 다른 것만 알림
// - 처음(저장 값 없음)에는 지금 상태를 본 것으로 저장 → 예전 일이 한꺼번에 알림으로 뜨지 않음
// - 실제 회원만 (데모·비로그인은 서버 기록이 없음). 저장은 계정별 localStorage `notifySeen@<계정>`
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useAuth } from '../../components/auth';
import { readSetting, writeSetting } from '../../components/storage';
import type { KoEn } from '../../lib/common';
import { listMine, ykihoOf } from '../consult/bookingApi';
import { listAftercare } from '../aftercare/aftercareApi';
import { useHospitals } from '../hospital/useHospitals';
import { hospitalNames } from '../hospital/name';

const POLL_MS = 30_000;
// 환자에게 알릴 상태 (환자가 직접 한 취소·처음 대기는 제외)
const NOTIFY_STATUS = ['confirmed', 'rejected', 'proposed', 'visited', 'no_show', 'expired'] as const;
export type NotifyStatus = (typeof NOTIFY_STATUS)[number];

export type Notice =
  | { key: string; kind: 'status'; status: NotifyStatus; requestId: string; hospital?: KoEn; at: string; to: '/mypage/bookings' }
  | { key: string; kind: 'reply'; count: number; requestId: string; hospital?: KoEn; at: string; to: '/booking' }
  | { key: string; kind: 'aftercare'; count: number; requestId: string; hospital?: KoEn; at: string; to: '/aftercare' };

interface Seen {
  status: Record<string, string>; // 요청 id → 마지막으로 본 상태
  replies: Record<string, number>; // 요청 id → 본 답장 수
  aftercare: Record<string, string>; // 요청 id → 본 마지막 메시지 시각
}

interface Snapshot {
  bookings: { id: string; status: string; replies: number; lastReplyAt?: string; hospitalId: number; updatedAt: string }[];
  aftercare: { requestId: string; lastAt: string; unread: number }[];
}

interface Ctx {
  notices: Notice[];
  markRead: (n: Notice) => void;
  markAll: () => void;
  countFor: (to: Notice['to']) => number;
}

const NotificationsContext = createContext<Ctx>({ notices: [], markRead: () => {}, markAll: () => {}, countFor: () => 0 });
export const useNotifications = () => useContext(NotificationsContext);

const seenKey = (account: string) => `notifySeen@${account}`;
function readSeen(account: string): Seen | null {
  try {
    const v = JSON.parse(readSetting(seenKey(account)) ?? 'null');
    return v && typeof v === 'object' ? { status: v.status ?? {}, replies: v.replies ?? {}, aftercare: v.aftercare ?? {} } : null;
  } catch {
    return null;
  }
}
const writeSeen = (account: string, seen: Seen) => writeSetting(seenKey(account), JSON.stringify(seen));

function seenFrom(s: Snapshot): Seen {
  return {
    status: Object.fromEntries(s.bookings.map((b) => [b.id, b.status])),
    replies: Object.fromEntries(s.bookings.map((b) => [b.id, b.replies])),
    aftercare: Object.fromEntries(s.aftercare.map((a) => [a.requestId, a.lastAt])),
  };
}

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const { user, account, token } = useAuth();
  const member = !!user && !user.demo && !!token;
  const hospitals = useHospitals();
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [seen, setSeen] = useState<Seen | null>(null);
  const [names, setNames] = useState<Record<number, string>>({}); // 백엔드 병원 id → ykiho
  const accountRef = useRef(account);
  accountRef.current = account;

  // 계정이 바뀌면 처음부터
  useEffect(() => {
    setSnap(null);
    setSeen(member ? readSeen(account) : null);
  }, [account, member]);

  const load = useCallback(async () => {
    if (!member || !token) return;
    const key = account;
    const [mine, care] = await Promise.all([listMine(token), listAftercare(token).catch(() => [])]);
    if (accountRef.current !== key) return;
    const next: Snapshot = {
      bookings: mine.map((b) => {
        const replies = (b as { replies?: { sent_at: string }[] }).replies ?? []; // 답장 API가 있는 서버에서만
        return { id: b.id, status: b.status, replies: replies.length, lastReplyAt: replies[replies.length - 1]?.sent_at, hospitalId: b.hospital_id, updatedAt: b.created_at };
      }),
      // 병원이 보낸 새 메시지(내가 마지막으로 보낸 뒤)가 있는 대화만
      aftercare: care.map((t) => ({ requestId: t.request_id, lastAt: t.last_message_at, unread: t.unread })),
    };
    setSnap(next);
    setSeen((prev) => {
      if (prev) return prev;
      const first = seenFrom(next); // 처음: 지금 상태를 본 것으로
      writeSeen(key, first);
      return first;
    });
    const ids = [...new Set(next.bookings.map((b) => b.hospitalId))];
    const pairs = await Promise.all(ids.map(async (id) => [id, await ykihoOf(id).catch(() => undefined)] as const));
    if (accountRef.current === key) setNames(Object.fromEntries(pairs.filter(([, y]) => y)) as Record<number, string>);
  }, [member, token, account]);

  // 30초마다 + 탭으로 돌아올 때
  useEffect(() => {
    if (!member) return;
    load().catch(() => {});
    const timer = window.setInterval(() => document.visibilityState === 'visible' && load().catch(() => {}), POLL_MS);
    const onFocus = () => load().catch(() => {});
    window.addEventListener('focus', onFocus);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('focus', onFocus);
    };
  }, [member, load]);

  const notices = useMemo<Notice[]>(() => {
    if (!snap || !seen) return [];
    const byYkiho = hospitals.status === 'ready' ? new Map(hospitals.data.items.map((h) => [h.id, h])) : new Map();
    const nameOf = (hospitalId: number) => {
      const h = byYkiho.get(names[hospitalId]);
      return h ? hospitalNames(h) : undefined;
    };
    const hospitalOfRequest = new Map(snap.bookings.map((b) => [b.id, b.hospitalId]));
    const out: Notice[] = [];
    for (const b of snap.bookings) {
      const before = seen.status[b.id];
      if (b.status !== before && (NOTIFY_STATUS as readonly string[]).includes(b.status)) {
        out.push({ key: `status:${b.id}:${b.status}`, kind: 'status', status: b.status as NotifyStatus, requestId: b.id, hospital: nameOf(b.hospitalId), at: b.updatedAt, to: '/mypage/bookings' });
      }
      const newReplies = b.replies - (seen.replies[b.id] ?? 0);
      if (newReplies > 0) {
        out.push({ key: `reply:${b.id}:${b.replies}`, kind: 'reply', count: newReplies, requestId: b.id, hospital: nameOf(b.hospitalId), at: b.lastReplyAt ?? b.updatedAt, to: '/booking' });
      }
    }
    for (const a of snap.aftercare) {
      if (a.unread > 0 && a.lastAt !== seen.aftercare[a.requestId]) {
        const hid = hospitalOfRequest.get(a.requestId);
        out.push({ key: `aftercare:${a.requestId}:${a.lastAt}`, kind: 'aftercare', count: a.unread, requestId: a.requestId, hospital: hid ? nameOf(hid) : undefined, at: a.lastAt, to: '/aftercare' });
      }
    }
    return out.sort((x, y) => y.at.localeCompare(x.at));
  }, [snap, seen, names, hospitals]);

  const save = useCallback(
    (fn: (s: Seen) => Seen) =>
      setSeen((prev) => {
        if (!prev) return prev;
        const next = fn(prev);
        writeSeen(accountRef.current, next);
        return next;
      }),
    [],
  );

  const markRead = useCallback(
    (n: Notice) => {
      const b = snap?.bookings.find((x) => x.id === n.requestId);
      const a = snap?.aftercare.find((x) => x.requestId === n.requestId);
      save((s) =>
        n.kind === 'status' && b ? { ...s, status: { ...s.status, [b.id]: b.status } }
        : n.kind === 'reply' && b ? { ...s, replies: { ...s.replies, [b.id]: b.replies } }
        : n.kind === 'aftercare' && a ? { ...s, aftercare: { ...s.aftercare, [a.requestId]: a.lastAt } }
        : s,
      );
    },
    [snap, save],
  );

  const markAll = useCallback(() => {
    if (snap) save(() => seenFrom(snap));
  }, [snap, save]);

  const countFor = useCallback((to: Notice['to']) => notices.filter((n) => n.to === to).length, [notices]);

  const value = useMemo(() => ({ notices, markRead, markAll, countFor }), [notices, markRead, markAll, countFor]);
  return <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>;
}

/** 그 화면을 열면 그 화면의 알림은 읽은 것으로 (예: 예약 관리를 열면 상태 알림) */
export function useMarkSeenOn(to: Notice['to']) {
  const { notices, markRead } = useNotifications();
  useEffect(() => {
    notices.filter((n) => n.to === to).forEach(markRead);
  }, [notices, to, markRead]);
}
