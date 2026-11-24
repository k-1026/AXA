import type { DepartmentKey } from '../hospital/types';
import type { ChatText } from '../chatbot/types';

// 병원 1곳 = 상담 1개. 날짜가 달라도 같은 병원과의 대화는 한 상담에 이어서 쌓인다
// 예약 요청 상태 = 백엔드 계약 (docs/backend-contracts.md 2절)
// pending 대기 · confirmed 확정 · rejected 병원 거절 · proposed 병원이 다른 시간 제안 · cancelled 환자 취소 · expired 희망 날짜가 모두 지남
// visited 병원이 방문 완료 표시 · no_show 병원이 미방문 표시 (결정 19, 병원 직원만 바꿈)
export type BookingStatus = 'pending' | 'confirmed' | 'rejected' | 'proposed' | 'cancelled' | 'expired' | 'visited' | 'no_show';

// 화면 표시용 상태
export type DisplayStatus = BookingStatus;

// 서버 예약(serverId 있음)은 병원이 표시한 상태 그대로 — 확정 뒤 시간이 지나도 병원이 방문 완료를 누르기 전까지는 "확정"
// 서버에 없는 데모 계정 예약만 예전처럼 확정 + 방문 일시(한국 시간) 지남 → 방문 완료로 봄 (사후관리 예시용)
export function displayStatus(b: Pick<BookingRequest, 'status' | 'date' | 'time' | 'serverId'>, now = Date.now()): DisplayStatus {
  if (!b.serverId && b.status === 'confirmed' && Date.parse(`${b.date}T${b.time}:00+09:00`) <= now) return 'visited';
  return b.status;
}

export interface BookingRequest {
  date: string; // YYYY-MM-DD (한국 시간)
  time: string; // HH:mm
  language: string; // 상담 언어 코드 (ko·en·zh-CN·zh-TW·vi)
  note?: string;
  status: BookingStatus; // 확정은 병원만 할 수 있다 (기본값 pending). 취소는 환자가 할 수 있다
  bookingNo?: string; // 병원이 확정하면 붙는 예약번호
  cancelledAt?: string; // ISO 시각
  treatment?: ChatText; // 병원이 기록한 진료·시술 이름 (방문 완료로 보일 때 표시)
  serverId?: string; // 실제 회원: 백엔드 예약 요청 id (POST /hospitals/{id}/booking-requests)
  rejectReason?: RejectReason; // 거절 사유 코드 (병원이 고름, 없을 수 있음)
}

// 병원 거절 사유 (docs/backend-contracts.md 2절) → 문장은 bookings.rejectReason.*
export type RejectReason = 'fully_booked' | 'not_offered' | 'needs_consult' | 'other';

interface ConsultMessage {
  id: string;
  from: 'staff' | 'user';
  text?: ChatText;
  booking?: BookingRequest;
  at: string; // ISO 시각
}

export interface ConsultThread {
  hospitalId: string;
  name: ChatText;
  dept: DepartmentKey;
  district: string; // 구군 키 (i18n district.*)
  photo?: string;
  messages: ConsultMessage[];
  unread: number; // 아직 읽지 않은 병원 답변 수
  sample?: boolean; // 예시 병원·대화 (실제 상담 기록 아님)
}
