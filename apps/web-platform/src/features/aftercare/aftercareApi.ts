// 환자 사후관리 API (docs/backend-contracts.md 6-3절). 예약 요청 1건(방문 완료) = 대화 1개
// 사진·영상 파일은 서버에 아직 저장하지 않음 → "사진 있음"(photo)만 보내고, 미리보기는 이 탭에서만
import { api } from '../../components/api';
import type { AftercareMessage } from './types';

interface ServerMessage {
  id: number;
  sender: 'patient' | 'staff';
  text_original: string;
  text_translated: string | null;
  has_photo: boolean;
  created_at: string;
}

export interface ServerThread {
  id: string;
  request_id: string;
  status: string;
  last_message_at: string;
  last_message: string | null;
  unread: number;
  messages: ServerMessage[] | null;
}

export const PHOTO_ONLY = '📷'; // 글 없이 사진만 보낼 때 (서버는 글이 꼭 있어야 함)

export const toLocalMessage = (m: ServerMessage): AftercareMessage => ({
  id: `srv-${m.id}`,
  from: m.sender === 'staff' ? 'doctor' : 'user',
  at: m.created_at,
  text: m.sender === 'patient' && m.has_photo && m.text_original === PHOTO_ONLY ? undefined : m.text_translated || m.text_original,
});

export const listAftercare = (token: string) => api<ServerThread[]>('/me/aftercare', { token });

export const getAftercare = (token: string, requestId: string) =>
  api<ServerThread>(`/me/booking-requests/${requestId}/aftercare`, { token });

export const sendAftercare = (token: string, requestId: string, text: string, photo: boolean) =>
  api<ServerThread>(`/me/booking-requests/${requestId}/aftercare/messages`, {
    method: 'POST',
    token,
    body: { text: text || PHOTO_ONLY, photo },
  });
