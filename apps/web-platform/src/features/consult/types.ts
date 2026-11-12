import type { DepartmentKey } from '../hospital/types';
import type { ChatText } from '../chatbot/types';

// 병원 1곳 = 상담 1개. 날짜가 달라도 같은 병원과의 대화는 한 상담에 이어서 쌓인다
// 예약 요청 상태 = 백엔드 계약 (docs/backend-contracts.md 2절)
// pending 대기 · confirmed 확정 · rejected 병원 거절 · proposed 병원이 다른 시간 제안 · cancelled 환자 취소 · expired 희망 날짜가 모두 지남
export type BookingStatus = 'pending' | 'confirmed' | 'rejected' | 'proposed' | 'cancelled' | 'expired';

// 화면 표시용 상태. 계약에는 "방문 완료" 상태가 없어서, 확정(confirmed)된 예약의 방문 일시(한국 시간)가 지나면
// 방문 완료(visited)로 보고 사후 관리 대상으로 삼는다. 병원이 방문 완료를 따로 표시하는 상태가 계약에 생기면 그것으로 바꾼다
export type DisplayStatus = BookingStatus | 'visited';

export function displayStatus(b: Pick<BookingRequest, 'status' | 'date' | 'time'>, now = Date.now()): DisplayStatus {
  if (b.status === 'confirmed' && Date.parse(`${b.date}T${b.time}:00+09:00`) <= now) return 'visited';
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
}

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
