// 사이트 안 알림 (결정 27): 서버 알림 표(GET /me/notifications) + Supabase Realtime으로 새 알림을 바로 받음
// - 병원이 예약 상태를 바꾸거나 답장하면 서버가 같은 처리 안에서 알림 한 줄을 씀 → 읽음 여부도 서버에 (기기마다 같음)
// - Realtime: 백엔드가 준 짧은 토큰으로 notifications 표의 새 줄만 구독 (RLS = 자기 알림만, 표에는 글·건강정보 없음)
// - Realtime을 쓸 수 없으면(설정 없음·연결 끊김) 60초마다·탭으로 돌아올 때 다시 불러옴
// - 실제 회원만 (데모·비로그인은 서버 기록이 없음)
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { createClient, type RealtimeChannel, type SupabaseClient } from '@supabase/supabase-js';
import { api } from '../../components/api';
import { useAuth } from '../../components/auth';
import type { KoEn } from '../../lib/common';
import { ykihoOf } from '../consult/bookingApi';
import { useHospitals } from '../hospital/useHospitals';
import { hospitalNames } from '../hospital/name';

const FALLBACK_MS = 60_000;
const PUBLISHABLE_KEY = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

export type NotifyStatus = 'confirmed' | 'rejected' | 'proposed' | 'visited' | 'no_show' | 'expired';
// 방문 전 리마인드 단계 (kind=reminder, backend notification/reminders.py)
export type ReminderStage = '48h' | '24h' | '2h';
type Target = '/mypage/bookings' | '/booking' | '/aftercare';

interface ServerNotice {
  id: number;
  kind: 'status' | 'reply' | 'aftercare' | 'reminder';
  request_id: string;
  hospital_id: number | null;
  status: NotifyStatus | ReminderStage | null;
  created_at: string;
  read: boolean;
}

export type Notice = {
  key: string;
  ids: number[]; // 같은 예약의 같은 종류는 한 줄로 묶음 (예: 답장 3개)
  kind: ServerNotice['kind'];
  status?: NotifyStatus | ReminderStage;
  count: number;
  requestId: string;
  hospital?: KoEn;
  at: string;
  to: Target;
};

interface Ctx {
  notices: Notice[];
  markRead: (n: Notice) => void;
  markAll: () => void;
  countFor: (to: Target) => number;
  live: boolean; // Realtime 연결됨
}

const NotificationsContext = createContext<Ctx>({ notices: [], markRead: () => {}, markAll: () => {}, countFor: () => 0, live: false });
export const useNotifications = () => useContext(NotificationsContext);

const TARGET: Record<ServerNotice['kind'], Target> = { status: '/mypage/bookings', reply: '/booking', aftercare: '/aftercare', reminder: '/mypage/bookings' };

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const { user, account, token } = useAuth();
  const member = !!user && !user.demo && !!token;
  const hospitals = useHospitals();
  const [rows, setRows] = useState<ServerNotice[]>([]);
  const [ykiho, setYkiho] = useState<Record<number, string>>({});
  const [live, setLive] = useState(false);
  const [epoch, setEpoch] = useState(0); // 바꾸면 Realtime 다시 연결 (토큰 만료 전·연결 끊김)
  const accountRef = useRef(account);
  accountRef.current = account;

  useEffect(() => setRows([]), [account]);

  const load = useCallback(async () => {
    if (!member || !token) return;
    const key = accountRef.current;
    const list = await api<ServerNotice[]>('/me/notifications', { token });
    if (accountRef.current !== key) return;
    setRows(list);
    const ids = [...new Set(list.map((n) => n.hospital_id).filter((x): x is number => x !== null))];
    const pairs = await Promise.all(ids.map(async (id) => [id, await ykihoOf(id).catch(() => undefined)] as const));
    if (accountRef.current === key) setYkiho(Object.fromEntries(pairs.filter(([, y]) => y)) as Record<number, string>);
  }, [member, token]);

  // 처음 + 탭으로 돌아올 때 + (Realtime이 없을 때만) 60초마다
  useEffect(() => {
    if (!member) return;
    load().catch(() => {});
    const onFocus = () => load().catch(() => {});
    window.addEventListener('focus', onFocus);
    const timer = live ? 0 : window.setInterval(() => document.visibilityState === 'visible' && load().catch(() => {}), FALLBACK_MS);
    return () => {
      window.removeEventListener('focus', onFocus);
      if (timer) window.clearInterval(timer);
    };
  }, [member, load, live]);

  // Realtime 구독: 새 알림 줄이 생기면 목록을 다시 불러옴 (병원 이름·묶음을 서버 기준으로 맞춤)
  useEffect(() => {
    if (!member || !token || !PUBLISHABLE_KEY) return;
    let client: SupabaseClient | null = null;
    let channel: RealtimeChannel | null = null;
    let refresh = 0;
    let stopped = false;
    (async () => {
      const rt = await api<{ url: string; token: string; expires_at: string }>('/me/notifications/realtime-token', { method: 'POST', token });
      if (stopped) return;
      client = createClient(rt.url, PUBLISHABLE_KEY, {
        auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
        accessToken: async () => rt.token,
      });
      client.realtime.setAuth(rt.token);
      const me = JSON.parse(atob(rt.token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).sub as string;
      channel = client
        .channel(`notifications:${me}`)
        .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'notifications', filter: `patient_id=eq.${me}` }, () => {
          load().catch(() => {});
        })
        .subscribe((status) => {
          if (stopped) return;
          setLive(status === 'SUBSCRIBED');
          if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT' || status === 'CLOSED') {
            window.clearTimeout(refresh);
            refresh = window.setTimeout(() => setEpoch((e) => e + 1), 30_000); // 30초 뒤 다시 (그동안은 60초 확인)
          }
        });
      // 토큰(1시간)이 끝나기 5분 전에 새 토큰으로 다시 연결
      const ms = Math.max(60_000, Date.parse(rt.expires_at) - Date.now() - 5 * 60_000);
      refresh = window.setTimeout(() => setEpoch((e) => e + 1), ms);
    })().catch(() => {
      if (stopped) return;
      setLive(false);
      refresh = window.setTimeout(() => setEpoch((e) => e + 1), 60_000);
    });
    return () => {
      stopped = true;
      window.clearTimeout(refresh);
      if (channel && client) client.removeChannel(channel);
      setLive(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- load는 token과 같이 바뀜 (넣으면 매번 다시 연결)
  }, [member, token, epoch]);

  const notices = useMemo<Notice[]>(() => {
    const byYkiho = hospitals.status === 'ready' ? new Map(hospitals.data.items.map((h) => [h.id, h])) : new Map();
    const nameOf = (hid: number | null) => {
      const h = hid === null ? undefined : byYkiho.get(ykiho[hid]);
      return h ? hospitalNames(h) : undefined;
    };
    const groups = new Map<string, Notice>();
    for (const n of rows) {
      if (n.read) continue;
      const key = n.kind === 'status' || n.kind === 'reminder' ? `${n.kind}:${n.request_id}:${n.id}` : `${n.kind}:${n.request_id}`;
      const g = groups.get(key);
      if (g) {
        g.ids.push(n.id);
        g.count += 1;
      } else {
        groups.set(key, {
          key, ids: [n.id], kind: n.kind, status: n.status ?? undefined, count: 1, requestId: n.request_id,
          hospital: nameOf(n.hospital_id), at: n.created_at, to: TARGET[n.kind],
        });
      }
    }
    return [...groups.values()].sort((a, b) => b.at.localeCompare(a.at));
  }, [rows, ykiho, hospitals]);

  const read = useCallback(
    (ids: number[] | null) => {
      if (!token) return;
      setRows((prev) => prev.map((n) => (ids === null || ids.includes(n.id) ? { ...n, read: true } : n))); // 바로 반영
      api('/me/notifications/read', { method: 'POST', token, body: { ids } }).catch(() => load().catch(() => {}));
    },
    [token, load],
  );

  const markRead = useCallback((n: Notice) => read(n.ids), [read]);
  const markAll = useCallback(() => read(null), [read]);
  const countFor = useCallback((to: Target) => notices.filter((n) => n.to === to).length, [notices]);

  const value = useMemo(() => ({ notices, markRead, markAll, countFor, live }), [notices, markRead, markAll, countFor, live]);
  return <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>;
}

/** 그 화면을 열면 그 화면의 알림은 읽은 것으로 (예: 예약 관리를 열면 상태 알림) */
export function useMarkSeenOn(to: Target) {
  const { notices, markRead } = useNotifications();
  useEffect(() => {
    notices.filter((n) => n.to === to).forEach(markRead);
  }, [notices, to, markRead]);
}
