import { useSyncExternalStore } from 'react';
import { createAccountList } from '../../components/account';

// 찜한 병원. 찜 백엔드 연결 전이라 지금은 이 브라우저에만 저장한다
interface SavedEntry {
  id: string;
  savedAt: string; // ISO 시각, "최근 저장순" 정렬용
}

// 계정별로 따로 저장 (로그인 전·데모·회원마다 다른 목록). 탈퇴하면 그 계정 목록은 지움
const store = createAccountList<SavedEntry>('savedHospitals');

function toggle(id: string) {
  const entries = store.get();
  store.set(
    entries.some((e) => e.id === id) ? entries.filter((e) => e.id !== id) : [...entries, { id, savedAt: new Date().toISOString() }],
  );
}

export function useSavedHospitals() {
  const saved = useSyncExternalStore(store.subscribe, store.get);
  return { saved, isSaved: (id: string) => saved.some((e) => e.id === id), toggle };
}
