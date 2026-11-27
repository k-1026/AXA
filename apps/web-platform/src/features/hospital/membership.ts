import type { Hospital } from './types';

// 지도 표시용 병원 회원 구분 (2026-11-27)
// - 입점 병원 = 메디대구에 입점한 병원. 지금은 시연용 예시 병원 4곳(hospitals.json의 demo)
// - 프리미엄 회원 = 요금안 v4의 프리미엄(연 ₩1,800,000 + 수수료 8%)을 결제한 입점 병원
//   결제·회원 등급 자료가 아직 백엔드에 없어서 시연용으로 정한 가정값. 결제 자료가 생기면 이 표 대신 그 값을 쓴다
export const PREMIUM_HOSPITAL_IDS: ReadonlySet<string> = new Set(['DEMO-9001', 'DEMO-9003']);

export type Membership = 'premium' | 'partner' | null;

export function membershipOf(h: Hospital): Membership {
  if (!h.demo) return null;
  return PREMIUM_HOSPITAL_IDS.has(h.id) ? 'premium' : 'partner';
}
