// 상담 화면 날짜 표시 (한국 시간)
import { KST as TZ } from '../../lib/common';

/** 목록 날짜: "11월 10일" / "Nov 10" */
export const shortDate = (iso: string, lang: string) =>
  new Intl.DateTimeFormat(lang, { timeZone: TZ, month: 'short', day: 'numeric' }).format(new Date(iso));

/** 예약 일시: "11월 14일 (토) 오후 2:00" — 날짜·시간은 한국 시간 그대로 */
export function bookingDateTime(date: string, time: string, lang: string) {
  const d = new Date(`${date}T${time}:00+09:00`);
  const day = new Intl.DateTimeFormat(lang, { timeZone: TZ, month: 'long', day: 'numeric', weekday: 'short' }).format(d);
  const hm = new Intl.DateTimeFormat(lang, { timeZone: TZ, hour: 'numeric', minute: '2-digit' }).format(d);
  return `${day} ${hm}`;
}

/** 예약 관리 날짜: "2026.11.14 (토) 오후 2:00" */
export function bookingDateFull(date: string, time: string, lang: string) {
  const d = new Date(`${date}T${time}:00+09:00`);
  const wd = new Intl.DateTimeFormat(lang, { timeZone: TZ, weekday: 'short' }).format(d);
  const hm = new Intl.DateTimeFormat(lang, { timeZone: TZ, hour: 'numeric', minute: '2-digit' }).format(d);
  return `${date.replace(/-/g, '.')} (${wd}) ${hm}`;
}

/** 지금 시각 (HH:mm, 한국 시간) */
export const nowKstTime = () =>
  new Intl.DateTimeFormat('en-GB', { timeZone: TZ, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date());
