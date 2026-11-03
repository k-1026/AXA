// 날짜·시간은 모두 한국 시간(KST) 기준으로 표시
const TZ = 'Asia/Seoul';

/** YYYY-MM-DD (KST) */
export function kstDay(iso: string | Date): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' }).format(
    new Date(iso),
  );
}

/** 대화 제목: YYYY.MM.DD */
export const dotDate = (iso: string) => kstDay(iso).replace(/-/g, '.');

/** 목록 보조 정보: "오후 4:20" / "4:20 PM" */
export const listTime = (iso: string, lang: string) =>
  new Intl.DateTimeFormat(lang, { timeZone: TZ, hour: 'numeric', minute: '2-digit' }).format(new Date(iso));

/** 메시지 시각: 16:20 */
export const msgTime = (iso: string) =>
  new Intl.DateTimeFormat('en-GB', { timeZone: TZ, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(
    new Date(iso),
  );

/** 날짜 구분선: "2026년 11월 3일" / "November 3, 2026" */
export const longDate = (iso: string, lang: string) =>
  new Intl.DateTimeFormat(lang, { timeZone: TZ, dateStyle: 'long' }).format(new Date(iso));

/** 오늘·어제·이전 묶음 */
export function dayGroup(iso: string, now = new Date()): 'today' | 'yesterday' | 'earlier' {
  const day = kstDay(iso);
  if (day === kstDay(now)) return 'today';
  if (day === kstDay(new Date(now.getTime() - 86_400_000))) return 'yesterday';
  return 'earlier';
}
