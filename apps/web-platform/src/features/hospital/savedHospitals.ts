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

/** 지금 계정의 찜 목록이 비어 있을 때만 채움 (시연 계정 예시용, mypage/demoPatientSeed.ts) */
export function seedSavedIfEmpty(ids: string[]) {
  if (store.get().length) return;
  const now = Date.now();
  store.set(ids.map((id, i) => ({ id, savedAt: new Date(now - i * 86_400_000).toISOString() })));
}

export function useSavedHospitals() {
  const saved = useSyncExternalStore(store.subscribe, store.get);
  return { saved, isSaved: (id: string) => saved.some((e) => e.id === id), toggle };
}
