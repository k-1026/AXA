import type { BookingRequest } from './types';

// 중복 예약 규칙 — 백엔드 booking/service.py와 같은 기준 (docs/booking-rules.md)
// 서버가 최종 판단하고, 여기서는 보내기 전에 미리 막는다 (예시 로그인은 서버가 없으므로 여기서만 막힘)
// - 어느 병원이든 다른 예약 시간 앞뒤 60분 안에는 새 요청 불가
// - 같은 병원 같은 날은 1건
// - 처리 전 요청(확인 대기·시간 제안)은 5건까지
export const BUFFER_MINUTES = 60;
export const MAX_OPEN = 5;
const ACTIVE = new Set(['pending', 'proposed', 'confirmed']);
const OPEN = new Set(['pending', 'proposed']);

export interface HeldBooking {
  hospitalId: string;
  messageId: string;
  booking: BookingRequest;
}

export type BookingRuleCode = 'booking.time_conflict' | 'booking.same_day' | 'booking.too_many';

/** 규칙 위반을 서버 오류와 같은 코드로 던짐 → bookingErrorKey가 같은 문구로 바꿈 */
export class BookingRuleError extends Error {
  code: BookingRuleCode;
  constructor(code: BookingRuleCode) {
    super(code);
    this.code = code;
  }
}

// 날짜·시간은 모두 한국 시간 문자열 → 같은 기준으로 분 단위 비교
const minutes = (date: string, time: string) => Date.parse(`${date}T${time}:00Z`) / 60000;

/** 새 요청(target)이 내 다른 예약과 겹치면 오류. ignoreMessageId = 지금 바꾸는 그 예약 */
export function checkBookingRules(
  held: HeldBooking[],
  target: { hospitalId: string; date: string; time: string },
  ignoreMessageId?: string,
): void {
  const others = held.filter((h) => h.messageId !== ignoreMessageId && ACTIVE.has(h.booking.status));
  if (!ignoreMessageId && others.filter((h) => OPEN.has(h.booking.status)).length >= MAX_OPEN) {
    throw new BookingRuleError('booking.too_many');
  }
  const t = minutes(target.date, target.time);
  for (const h of others) {
    if (h.hospitalId === target.hospitalId && h.booking.date === target.date) throw new BookingRuleError('booking.same_day');
    if (Math.abs(minutes(h.booking.date, h.booking.time) - t) < BUFFER_MINUTES) throw new BookingRuleError('booking.time_conflict');
  }
}
