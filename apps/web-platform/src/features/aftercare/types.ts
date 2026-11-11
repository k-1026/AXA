import type { ChatText } from '../chatbot/types';

// 사후 관리 대화. 방문을 마친 예약 1건 = 대화 1개 (답변은 그 병원 의료진)
export interface Attachment {
  kind: 'image' | 'video';
  url: string; // 백엔드 연결 전: 이 탭에서만 쓰는 임시 주소 (blob:)
  name: string;
}

export interface AftercareMessage {
  id: string;
  from: 'doctor' | 'user';
  text?: ChatText;
  attachments?: Attachment[];
  at: string; // ISO 시각
}
