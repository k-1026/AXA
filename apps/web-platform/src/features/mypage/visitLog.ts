import { useSyncExternalStore } from 'react';
import { createAccountList } from '../../components/account';
import { uid } from '../../lib/common';

// 방문 기록(개인 다이어리). 본인만 쓰고 본인만 본다: 후기가 아니므로 서버로 보내거나 병원 화면에 표시하지 않는다
export interface VisitRecord {
  id: string;
  hospitalId?: string; // 목록에서 고른 병원. 직접 입력했으면 없음
  hospitalName: string;
  date: string; // YYYY-MM-DD
  note: string;
  createdAt: string; // 같은 날짜 안에서 정렬용
}

export type VisitInput = Pick<VisitRecord, 'hospitalId' | 'hospitalName' | 'date' | 'note'>;

// 계정별로 따로 저장 (로그인 전·데모·회원마다 다른 기록). 탈퇴하면 그 계정 기록은 지움
const store = createAccountList<VisitRecord>('visitLog');

const add = (input: VisitInput) =>
  store.set([
    ...store.get(),
    { ...input, id: uid(), createdAt: new Date().toISOString() },
  ]);
const update = (id: string, input: VisitInput) =>
  store.set(store.get().map((r) => (r.id === id ? { ...r, hospitalId: undefined, ...input } : r)));
const remove = (id: string) => store.set(store.get().filter((r) => r.id !== id));

export function useVisitLog() {
  const visits = useSyncExternalStore(store.subscribe, store.get);
  return { visits, add, update, remove };
}
