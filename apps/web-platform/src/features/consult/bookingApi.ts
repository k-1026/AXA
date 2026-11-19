// 예약 요청 API (docs/backend-contracts.md 6·6-1절). 흐름: 환자 예약 요청(대기) → 병원 확정 → 내 예약에 "확정"
// 화면의 병원 id는 심평원 요양기관 기호(ykiho), 백엔드 경로는 숫자 병원 id → 등록 병원 목록으로 바꿔서 부른다
import { api } from '../../components/api';
import type { BookingRequest, BookingStatus } from './types';

export const KST_OFFSET = '+09:00';
// 동의 문구 버전. privacy = 개인정보 처리방침 개정일, overseas_transfer = 번역(해외 AI) 안내 문구 날짜
export const OVERSEAS_VERSION = '2026-11-18';

interface ServerBooking {
  id: string;
  hospital_id: number;
  status: BookingStatus;
  lang: string;
  preferred_slots: string[];
  department_code: string;
  message_original: string | null;
  confirmed_slot: string | null;
  created_at: string;
}

interface HospitalRef {
  id: number;
  ykiho: string;
}

export interface BookingExtra {
  nationality: string; // ISO 2자리
  consents: { kind: 'privacy' | 'overseas_transfer'; version: string }[];
}

// 등록 병원 ykiho ↔ 백엔드 id (한 번만 불러 둠)
let refs: Promise<HospitalRef[]> | null = null;
const hospitalRefs = () => {
  refs ??= api<HospitalRef[]>('/hospitals?registered=true').catch((e) => {
    refs = null;
    throw e;
  });
  return refs;
};
export const serverIdOf = async (ykiho: string) => (await hospitalRefs()).find((h) => h.ykiho === ykiho)?.id;
export const ykihoOf = async (id: number) => (await hospitalRefs()).find((h) => h.id === id)?.ykiho;

// UTC ISO → 한국 날짜·시간
function kstParts(iso: string): { date: string; time: string } {
  const d = new Date(Date.parse(iso) + 9 * 3600_000).toISOString();
  return { date: d.slice(0, 10), time: d.slice(11, 16) };
}

export function toLocal(s: ServerBooking): BookingRequest {
  const when = kstParts(s.confirmed_slot ?? s.preferred_slots[0]);
  return {
    ...when,
    language: s.lang,
    note: s.message_original ?? undefined,
    status: s.status, // 방문 완료·미방문도 서버 상태 그대로 (결정 19)
    serverId: s.id,
    bookingNo: s.status === 'confirmed' || s.status === 'visited' ? s.id.slice(0, 8).toUpperCase() : undefined,
  };
}

export async function createBooking(
  token: string,
  ykiho: string,
  dept: string,
  b: Omit<BookingRequest, 'status'>,
  extra: BookingExtra,
): Promise<{ server: ServerBooking; local: BookingRequest }> {
  const id = await serverIdOf(ykiho);
  if (id === undefined) throw new Error('hospital.not_requestable');
  let timezone = 'Asia/Seoul';
  try {
    timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || timezone;
  } catch {
    /* 기본값 */
  }
  const server = await api<ServerBooking>(`/hospitals/${id}/booking-requests`, {
    method: 'POST',
    token,
    body: {
      department_code: dept,
      preferred_slots: [`${b.date}T${b.time}:00${KST_OFFSET}`],
      patient_timezone: timezone,
      lang: b.language,
      nationality: extra.nationality,
      contact_method: 'email',
      visa_needed: false,
      message: b.note || undefined,
      residency: 'short_term',
      consents: extra.consents,
    },
  });
  return { server, local: toLocal(server) };
}

export const listMine = (token: string) => api<ServerBooking[]>('/me/booking-requests', { token });

export const cancelMine = (token: string, serverId: string) =>
  api<ServerBooking>(`/me/booking-requests/${serverId}/cancel`, { method: 'POST', token, body: {} });

export type { ServerBooking };
