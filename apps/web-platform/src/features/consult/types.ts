import type { DepartmentKey } from '../hospital/types';
import type { ChatText } from '../chatbot/types';

// 병원 1곳 = 상담 1개. 날짜가 달라도 같은 병원과의 대화는 한 상담에 이어서 쌓인다
export type BookingStatus = 'pending' | 'confirmed' | 'declined' | 'cancelled';

export interface BookingRequest {
  date: string; // YYYY-MM-DD (한국 시간)
  time: string; // HH:mm
  language: string; // 상담 언어 코드 (ko·en·zh-CN·zh-TW·vi)
  note?: string;
  status: BookingStatus; // 확정은 병원만 할 수 있다 (기본값 pending). 취소는 환자가 할 수 있다
  bookingNo?: string; // 병원이 확정하면 붙는 예약번호
  cancelledAt?: string; // ISO 시각
}

export interface ConsultMessage {
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
