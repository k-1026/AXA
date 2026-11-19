import type { Hospital } from '../hospital/types';

// 예약 가능 날짜·시간 (예시). 병원 예약 일정(availability)이 연결되기 전이라
// 병원 진료시간(심평원) 안에서 30분 단위로 만들고, 일부 시간은 이미 찬 것으로 표시한다.
// 진료시간 정보가 없는 병원은 평일 09:00~18:00(점심 13:00~14:00)·토요일 09:00~13:00으로 둔다
export const DAYS_AHEAD = 60; // 오늘부터 고를 수 있는 날 수
const STEP = 30;

const toMin = (hhmm: string) => Number(hhmm.slice(0, 2)) * 60 + Number(hhmm.slice(3, 5));
const toHhmm = (m: number) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;

const DEFAULT_WEEK: ([string, string] | null)[] = [
  ['09:00', '18:00'], ['09:00', '18:00'], ['09:00', '18:00'], ['09:00', '18:00'], ['09:00', '18:00'], ['09:00', '13:00'], null,
];

// "12:30~13:30" 같은 점심시간 → [시작분, 끝분]
function lunch(text: string | undefined): [number, number] | null {
  const m = text?.match(/(\d{1,2}):(\d{2})\s*~\s*(\d{1,2}):(\d{2})/);
  return m ? [Number(m[1]) * 60 + Number(m[2]), Number(m[3]) * 60 + Number(m[4])] : null;
}

// 같은 병원·날짜·시간이면 항상 같은 결과 (새로고침해도 바뀌지 않게)
function hash(s: string) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return h >>> 0;
}

// YYYY-MM-DD → 월요일 0 … 일요일 6
export const weekdayIndex = (date: string) => (new Date(`${date}T00:00:00Z`).getUTCDay() + 6) % 7;

export function addDays(date: string, n: number) {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

export type Slot = { time: string; free: boolean };

export function slotsFor(h: Hospital, date: string, today: string, nowTime: string): Slot[] {
  const day = weekdayIndex(date);
  const week = h.hours ?? DEFAULT_WEEK;
  const range = week[day];
  if (!range) return [];
  const brk = h.hours ? lunch(day === 5 ? h.lunchSat : h.lunchWeek) : day === 5 ? null : ([13 * 60, 14 * 60] as [number, number]);
  const slots: Slot[] = [];
  for (let m = toMin(range[0]); m + STEP <= toMin(range[1]); m += STEP) {
    if (brk && m < brk[1] && m + STEP > brk[0]) continue;
    const time = toHhmm(m);
    if (date === today && time <= nowTime) continue;
    slots.push({ time, free: hash(`${h.id}|${date}|${time}`) % 100 >= 30 });
  }
  return slots;
}

export const isBookable = (h: Hospital, date: string, today: string, nowTime: string) =>
  date >= today && date <= addDays(today, DAYS_AHEAD - 1) && slotsFor(h, date, today, nowTime).some((s) => s.free);
