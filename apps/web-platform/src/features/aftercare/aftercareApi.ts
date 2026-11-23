// 환자 사후관리 API (docs/backend-contracts.md 6-3절). 예약 요청 1건(방문 완료) = 대화 1개
// 사진·영상: 서버가 준 서명된 주소로 Supabase Storage에 바로 올리고(uploads), 보낼 때 경로를 붙임 (결정 22)
// 저장소 설정이 없는 서버(503 storage.unavailable)면 예전처럼 "사진 있음"(photo)만 보내고 미리보기는 이 탭에서만
import { api, ApiError } from '../../components/api';
import { asJpgName, shrinkImage } from './shrinkImage';
import type { AftercareMessage, Attachment } from './types';

interface ServerMessage {
  id: number;
  sender: 'patient' | 'staff';
  text_original: string;
  text_translated: string | null;
  has_photo: boolean;
  // url = 1시간짜리 서명된 주소, thumb_url = 썸네일 (없으면 null → url을 씀, 결정 29)
  attachments?: { kind: 'image' | 'video'; name: string | null; url: string | null; thumb_url?: string | null }[];
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

export const toLocalMessage = (m: ServerMessage): AftercareMessage => {
  const files: Attachment[] = (m.attachments ?? [])
    .filter((a) => a.url)
    .map((a) => ({ kind: a.kind, url: a.url!, name: a.name ?? '', thumbUrl: a.thumb_url ?? undefined }));
  const photoOnly = m.sender === 'patient' && m.has_photo && m.text_original === PHOTO_ONLY;
  return {
    id: `srv-${m.id}`,
    from: m.sender === 'staff' ? 'doctor' : 'user',
    at: m.created_at,
    // 사진만 보낸 메시지는 사진을 보여 주고 글은 숨김 (사진 주소가 없으면 📷 표시)
    // 내 글은 내가 쓴 원문, 병원 글은 내 언어 번역(없으면 한국어 원문) — 결정 25
    text: photoOnly && files.length ? undefined : m.sender === 'patient' ? m.text_original : m.text_translated || m.text_original,
    attachments: files.length ? files : undefined,
  };
};

export const listAftercare = (token: string) => api<ServerThread[]>('/me/aftercare', { token });

export const getAftercare = (token: string, requestId: string) =>
  api<ServerThread>(`/me/booking-requests/${requestId}/aftercare`, { token });

export interface SentFile {
  path: string;
  kind: 'image' | 'video';
  name: string;
  thumb?: boolean; // 썸네일도 올림 (사진만)
}

export const sendAftercare = (token: string, requestId: string, text: string, photo: boolean, attachments: SentFile[] = []) =>
  api<ServerThread>(`/me/booking-requests/${requestId}/aftercare/messages`, {
    method: 'POST',
    token,
    body: { text: text || PHOTO_ONLY, photo, attachments },
  });

const put = async (url: string, body: Blob) => {
  const res = await fetch(url, { method: 'PUT', headers: { 'Content-Type': body.type }, body });
  if (!res.ok) throw new ApiError(res.status, 'storage.upload_failed');
};

// 첨부 1개 올리기: 업로드 주소 받기 → Supabase에 바로 PUT. 저장소가 꺼진 서버면 null (사진 있음 표시만)
// 사진은 먼저 줄이고(1600px JPEG) 썸네일(360px)을 같이 올림 — 결정 29. 읽지 못하는 형식이면 원본 그대로
export async function uploadAftercare(token: string, requestId: string, a: Attachment): Promise<SentFile | null> {
  const original = await (await fetch(a.url)).blob(); // 이 탭의 미리보기(blob:) → 파일
  const small = a.kind === 'image' ? await shrinkImage(original) : null;
  const file = small?.main ?? original;
  const name = small ? asJpgName(a.name) : a.name;
  let up: { path: string; kind: 'image' | 'video'; upload_url: string; thumb_upload_url?: string | null };
  try {
    up = await api(`/me/booking-requests/${requestId}/aftercare/uploads`, {
      method: 'POST',
      token,
      body: { name, content_type: file.type, size: file.size, thumb: !!small },
    });
  } catch (e) {
    if (e instanceof ApiError && e.code === 'storage.unavailable') return null;
    throw e;
  }
  await put(up.upload_url, file);
  // 썸네일은 실패해도 원본으로 보이므로 보내기는 계속함
  let thumb = false;
  if (small && up.thumb_upload_url) thumb = await put(up.thumb_upload_url, small.thumb).then(() => true, () => false);
  return { path: up.path, kind: up.kind, name, ...(thumb ? { thumb: true } : {}) };
}
