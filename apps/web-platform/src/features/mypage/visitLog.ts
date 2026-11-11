import { useSyncExternalStore } from 'react';
import { readSetting, writeSetting } from '../../components/storage';

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

const KEY = 'visitLog';

function read(): VisitRecord[] {
  try {
    const parsed = JSON.parse(readSetting(KEY) ?? '[]');
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

let records = read();
const listeners = new Set<() => void>();

function commit(next: VisitRecord[]) {
  records = next;
  writeSetting(KEY, JSON.stringify(records));
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

const add = (input: VisitInput) =>
  commit([
    ...records,
    { ...input, id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`, createdAt: new Date().toISOString() },
  ]);
const update = (id: string, input: VisitInput) =>
  commit(records.map((r) => (r.id === id ? { ...r, hospitalId: undefined, ...input } : r)));
const remove = (id: string) => commit(records.filter((r) => r.id !== id));

export function useVisitLog() {
  const visits = useSyncExternalStore(subscribe, () => records);
  return { visits, add, update, remove };
}
