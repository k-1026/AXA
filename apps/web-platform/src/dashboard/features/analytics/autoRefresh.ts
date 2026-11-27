import { useEffect, useState } from 'react';
import { createClient, type RealtimeChannel, type SupabaseClient } from '@supabase/supabase-js';
import { API_BASE } from '../../../components/api';
import { readStaffToken } from '../../../features/staff/staffSession';

// 대시보드 자동 새로고침
// - 11/27 실시간: 환자가 요청·취소·수락·질문·사후관리 글을 보내면 서버가 staff_notifications에 한 줄 → Supabase Realtime으로
//   바로 받아(보통 1초 안) 숫자를 올림. 환자 알림(NotificationsProvider)과 같은 방식, 토큰은 POST /tenant/notifications/realtime-token
// - 11/26 확인용: 화면이 보일 때 30초마다 + 다른 탭·창에서 돌아올 때. 실시간 연결이 끊겼거나 설정이 없을 때를 대비해 그대로 둔다
// 이 숫자를 useEffect 의존값에 넣으면 다시 불러옴. 탭이 숨겨져 있을 때는 30초 확인을 하지 않는다 (서버 부담·Vercel 함수 호출 줄이기)
export const AUTO_REFRESH_MS = 30_000;
const RETRY_MS = 30_000;
const PUBLISHABLE_KEY = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

// 실시간 연결은 화면 전체에 하나만 (요청 목록·달력·상태 칸·오늘 할 일이 같이 씀)
let liveCount = 0;
const listeners = new Set<() => void>();
let started = false;
let client: SupabaseClient | null = null;
let channel: RealtimeChannel | null = null;
let timer = 0;

const bump = () => {
  liveCount += 1;
  listeners.forEach((f) => f());
};

function reconnect(ms: number) {
  window.clearTimeout(timer);
  timer = window.setTimeout(() => void connect(), ms);
}

async function connect() {
  if (channel && client) await client.removeChannel(channel).catch(() => {});
  channel = null;
  const token = readStaffToken();
  if (!token || !PUBLISHABLE_KEY) return; // 로그인 전이거나 설정 없음 → 30초 확인만
  try {
    const res = await fetch(`${API_BASE}/tenant/notifications/realtime-token`, { method: 'POST', headers: { Authorization: 'Bearer ' + token } });
    if (!res.ok) return reconnect(res.status === 401 ? 5 * 60_000 : RETRY_MS);
    const rt = (await res.json()) as { url: string; token: string; expires_at: string };
    client = createClient(rt.url, PUBLISHABLE_KEY, {
      auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
      accessToken: async () => rt.token,
    });
    client.realtime.setAuth(rt.token);
    const tenant = JSON.parse(atob(rt.token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).tenant_id as string;
    channel = client
      .channel(`staff-notifications:${tenant}`)
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'staff_notifications', filter: `tenant_id=eq.${tenant}` }, bump)
      .subscribe((status) => {
        if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT' || status === 'CLOSED') reconnect(RETRY_MS);
      });
    // 토큰(1시간)이 끝나기 5분 전에 새 토큰으로 다시 연결
    reconnect(Math.max(60_000, Date.parse(rt.expires_at) - Date.now() - 5 * 60_000));
  } catch {
    reconnect(RETRY_MS);
  }
}

export function useAutoRefresh(ms = AUTO_REFRESH_MS): number {
  const [n, setN] = useState(0);
  const [live, setLive] = useState(liveCount);
  useEffect(() => {
    const tick = () => { if (document.visibilityState === 'visible') setN((x) => x + 1); };
    const t = window.setInterval(tick, ms);
    document.addEventListener('visibilitychange', tick);
    return () => {
      window.clearInterval(t);
      document.removeEventListener('visibilitychange', tick);
    };
  }, [ms]);
  useEffect(() => {
    const on = () => setLive(liveCount);
    listeners.add(on);
    if (!started && readStaffToken()) { // 직원 로그인 뒤 처음 쓰일 때 한 번 연결
      started = true;
      void connect();
    }
    return () => { listeners.delete(on); };
  }, []);
  return n + live;
}
