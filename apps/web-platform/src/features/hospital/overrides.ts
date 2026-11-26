// 병원이 대시보드 "마이 병원"에서 직접 고친 병원 정보 (환자 병원 상세 페이지에 반영)
// 지금은 백엔드 API가 없어 이 브라우저(localStorage)에만 저장 → 같은 브라우저의 환자 화면에서만 보임
// 백엔드가 생기면 readOverrides·saveOverride만 API로 바꾸면 됨 (useHospitals·대시보드는 그대로)
import type { Hospital } from './types';

/** 병원이 고칠 수 있는 칸 (공공데이터 원본 위에 덮어씀) */
export type HospitalEdit = Partial<Pick<Hospital,
  'addr' | 'tel' | 'url' | 'instagram' | 'hours' | 'lunchWeek' | 'lunchSat' | 'rcvWeek' | 'rcvSat' | 'sunday' | 'holiday'
  | 'parking' | 'parkingFee' | 'email' | 'languages' | 'parkingNote'>> & { editedAt?: string };

const KEY = 'md.hospitalOverrides';

export function readOverrides(): Record<string, HospitalEdit> {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '{}') as Record<string, HospitalEdit>;
  } catch {
    return {};
  }
}

export function saveOverride(id: string, edit: HospitalEdit) {
  const all = readOverrides();
  all[id] = { ...edit, editedAt: new Date().toISOString() };
  try { localStorage.setItem(KEY, JSON.stringify(all)); } catch { /* 저장 못 하는 환경: 무시 */ }
}

export function clearOverride(id: string) {
  const all = readOverrides();
  delete all[id];
  try { localStorage.setItem(KEY, JSON.stringify(all)); } catch { /* 무시 */ }
}

/** 원본 + 병원 수정값 (빈 칸으로 저장한 건 지운 것으로 봄) */
export function applyOverride(h: Hospital, all = readOverrides()): Hospital {
  const e = all[h.id];
  if (!e) return h;
  const out: Hospital = { ...h, edited: true };
  for (const [k, v] of Object.entries(e)) {
    if (k === 'editedAt') continue;
    const key = k as keyof Hospital;
    if (v === '' || v === null || (Array.isArray(v) && !v.length && key !== 'hours')) delete (out as unknown as Record<string, unknown>)[key];
    else (out as unknown as Record<string, unknown>)[key] = v;
  }
  return out;
}
