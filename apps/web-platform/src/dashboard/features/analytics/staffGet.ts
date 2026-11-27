// 대시보드 GET 묶기 (11/27)
// - 여러 카드(오늘 할 일·예약 현황·달력·요청 목록·채팅)가 같은 주소를 같이 부르면 서버에는 한 번만 보냄
// - 받은 값은 2초 동안 같이 씀. 새 요청 신호·처리(확정 등) 뒤에는 clearStaffGet()으로 비워 새로 받음
// - 동시에 나가는 요청 수를 MAX_PARALLEL로 제한 (처음 접속 때 30개 넘게 한꺼번에 나가 서버·DB가 밀리던 것)
import { API_BASE } from '../../../components/api';
import { readStaffToken } from '../../../features/staff/staffSession';

export type StaffRes = { status: number; ok: boolean; body: any }; // 부르는 쪽에서 타입을 정함

const KEEP_MS = 2_000;
const MAX_PARALLEL = 6;
const cache = new Map<string, { done: number; p: Promise<StaffRes> }>(); // done: 받은 시각 (받는 중이면 Infinity)

let running = 0;
const waiting: (() => void)[] = [];
async function slot<T>(run: () => Promise<T>, first: boolean): Promise<T> {
  if (running >= MAX_PARALLEL) await new Promise<void>((r) => (first ? waiting.unshift(r) : waiting.push(r)));
  running += 1;
  try {
    return await run();
  } finally {
    running -= 1;
    waiting.shift()?.();
  }
}

// first: 화면 위쪽 숫자처럼 먼저 보여야 하는 것 → 기다리는 줄 맨 앞에
export function staffGet(path: string, { first = true } = {}): Promise<StaffRes> {
  const token = readStaffToken();
  const key = `${token} ${path}`;
  const hit = cache.get(key);
  if (hit && (hit.done === Infinity || Date.now() - hit.done < KEEP_MS)) return hit.p;
  const entry = { done: Infinity, p: null as unknown as Promise<StaffRes> };
  entry.p = slot(async () => {
    const res = await fetch(API_BASE + path, { headers: { Authorization: 'Bearer ' + token } });
    const body = await res.json().catch(() => ({}));
    return { status: res.status, ok: res.ok, body };
  }, first).then(
    (r) => { entry.done = Date.now(); if (!r.ok) cache.delete(key); return r; },
    (e) => { cache.delete(key); throw e; },
  );
  cache.set(key, entry);
  return entry.p;
}

export const clearStaffGet = () => cache.clear();
