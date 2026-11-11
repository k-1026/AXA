import { useSyncExternalStore } from 'react';
import { readSetting, writeSetting } from '../../components/storage';

// 찜한 병원. 회원 기능(백엔드) 연결 전이라 지금은 이 브라우저에만 저장한다
export interface SavedEntry {
  id: string;
  savedAt: string; // ISO 시각, "최근 저장순" 정렬용
}

const KEY = 'savedHospitals';

function read(): SavedEntry[] {
  try {
    const parsed = JSON.parse(readSetting(KEY) ?? '[]');
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

let entries = read();
const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function toggle(id: string) {
  entries = entries.some((e) => e.id === id)
    ? entries.filter((e) => e.id !== id)
    : [...entries, { id, savedAt: new Date().toISOString() }];
  writeSetting(KEY, JSON.stringify(entries));
  listeners.forEach((l) => l());
}

export function useSavedHospitals() {
  const saved = useSyncExternalStore(subscribe, () => entries);
  return { saved, isSaved: (id: string) => saved.some((e) => e.id === id), toggle };
}
