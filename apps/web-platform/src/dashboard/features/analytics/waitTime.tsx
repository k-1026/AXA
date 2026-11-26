// 답하지 않은 문의의 대기 시간 (진료시간 기준) → 신규·주의·위급 색 (상담 채팅·사후관리 채팅이 같이 씀)
// 단계: 신규 0~2시간 초록 #15803D · 주의 2~4시간 노랑 #F5B800 · 위급 4시간 이상 빨강 #DC2626 (팀 기준)
// 진료시간: 로그인한 병원 정보(hospitalProfile.ts)의 요일별 시간·점심시간
//   못 찾으면 평일 09:00~18:00 · 점심 12:30~13:30 (가정값)으로 계산
import { useEffect, useState } from 'react';
import { readStaffToken } from '../../../features/staff/staffSession';
import { loadHospitalProfile } from './hospitalProfile';

type Hours = { week: ([string, string] | null)[]; lunch: [string, string] | null; known: boolean };
const FALLBACK: Hours = {
  week: [['09:00', '18:00'], ['09:00', '18:00'], ['09:00', '18:00'], ['09:00', '18:00'], ['09:00', '18:00'], null, null],
  lunch: ['12:30', '13:30'],
  known: false,
};

function loadHours(): Promise<Hours> {
  return loadHospitalProfile(readStaffToken()).then((h) => (h?.hours ? { week: h.hours, lunch: h.lunch, known: true } : FALLBACK));
}

// 병원 진료시간 + 1분마다 다시 그리기용 현재 시각
export function useClinicClock() {
  const [hours, setHours] = useState<Hours>(FALLBACK);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    let alive = true;
    loadHours().then((h) => { if (alive) setHours(h); });
    const t = setInterval(() => setNow(Date.now()), 60_000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  return { hours, now };
}

const toMin = (hm: string) => +hm.slice(0, 2) * 60 + +hm.slice(3, 5);
const DAY = 864e5;

// from ~ to 사이에서 진료시간(점심 제외)에 해당하는 분 수 (한국 시간)
export function clinicMinutes(fromIso: string, to: number, h: Hours): number {
  const from = Date.parse(fromIso);
  if (!(from < to)) return 0;
  const kst = (t: number) => t + 9 * 3600e3;
  let total = 0;
  // 한국 날짜 0시(UTC 기준 값)부터 하루씩, 최대 60일
  let day = Math.floor(kst(from) / DAY) * DAY;
  const last = Math.floor(kst(to) / DAY) * DAY;
  for (let i = 0; day <= last && i < 60; day += DAY, i++) {
    const open = h.week[(new Date(day).getUTCDay() + 6) % 7];
    if (!open) continue;
    const spans: [number, number][] = h.lunch
      ? [[toMin(open[0]), Math.min(toMin(open[1]), toMin(h.lunch[0]))], [Math.max(toMin(open[0]), toMin(h.lunch[1])), toMin(open[1])]]
      : [[toMin(open[0]), toMin(open[1])]];
    for (const [a, b] of spans) {
      if (b <= a) continue;
      const s = Math.max(day + a * 60e3, kst(from));
      const e = Math.min(day + b * 60e3, kst(to));
      if (e > s) total += (e - s) / 60e3;
    }
  }
  return Math.floor(total);
}

export type WaitLevel = 'new' | 'warn' | 'urgent';
export const WAIT_LABEL: Record<WaitLevel, string> = { new: '신규', warn: '주의', urgent: '위급' };
export const waitLevel = (min: number): WaitLevel => (min < 120 ? 'new' : min < 240 ? 'warn' : 'urgent');
const dur = (min: number) => (min < 60 ? `${min}분` : `${Math.floor(min / 60)}시간${min % 60 ? ` ${min % 60}분` : ''}`);

export function WaitBadge({ min }: { min: number }) {
  const lv = waitLevel(min);
  return <span className={`wait wait-${lv}`} title={`진료시간 기준 대기 ${dur(min)}`}>{WAIT_LABEL[lv]} · {dur(min)}</span>;
}

export function WaitLegend({ known }: { known: boolean }) {
  return (
    <p className="wait-legend">
      <span><i className="wait-dot wait-new" />신규 0~2시간</span>
      <span><i className="wait-dot wait-warn" />주의 2~4시간</span>
      <span><i className="wait-dot wait-urgent" />위급 4시간 이상</span>
      <small>답하지 않은 대기 시간 · {known ? '이 병원 진료시간 기준' : '진료시간 기준 (병원 시간 못 찾음: 평일 9~18시로 계산)'}</small>
    </p>
  );
}
