import { useSyncExternalStore } from 'react';
import { createAccountList } from '../../components/account';
import { uid } from '../../lib/common';
import type { ScheduleItem } from './sampleData';

// 내가 직접 넣는 대구 여행 일정 (날짜 · 시간(선택) · 할 일). 서버 저장 전이라 계정별로 이 브라우저에만 저장
// 병원 예약은 예약 관리(서버)에 따로 있음 → 여기는 관광·쇼핑·이동 같은 내 계획
export interface TripPlan {
  id: string;
  date: string; // YYYY-MM-DD (한국 시간)
  time?: string; // HH:mm, 비우면 "하루 종일"
  text: string;
  createdAt: string;
}

export type TripPlanInput = Pick<TripPlan, 'date' | 'time' | 'text'>;

const store = createAccountList<TripPlan>('tripSchedule');

const add = (input: TripPlanInput) =>
  store.set([...store.get(), { ...input, time: input.time || undefined, id: uid(), createdAt: new Date().toISOString() }]);
const remove = (id: string) => store.set(store.get().filter((p) => p.id !== id));

/** 지금 계정의 일정이 비어 있을 때만 채움 (시연 계정 예시용, demoPatientSeed.ts) */
export function seedPlansIfEmpty(items: TripPlanInput[]) {
  if (store.get().length) return;
  store.set(items.map((input) => ({ ...input, id: uid(), createdAt: new Date().toISOString() })));
}

/** 화면의 일정 목록 모양으로 (시간 없는 일정은 그날 맨 앞) */
export const planToItem = (p: TripPlan): ScheduleItem => ({
  id: p.id,
  date: p.date,
  time: p.time ?? '',
  kind: 'plan',
  title: { ko: p.text, en: p.text },
  place: [],
  addedBy: 'user',
});

export const byDateTime = (a: ScheduleItem, b: ScheduleItem) => `${a.date} ${a.time}`.localeCompare(`${b.date} ${b.time}`);

export function useTripSchedule() {
  const plans = useSyncExternalStore(store.subscribe, store.get);
  return { plans, add, remove };
}
