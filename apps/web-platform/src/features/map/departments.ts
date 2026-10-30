import type { DepartmentKey } from '../hospital/types';

// ready: 지금 데이터로 걸러낼 수 있는지
// 내과는 심평원 진료과목 코드(01)를 아직 수집하지 않아서 준비 중
export const DEPARTMENTS: { key: DepartmentKey; ready: boolean }[] = [
  { key: 'dermatology', ready: true },
  { key: 'plastic', ready: true },
  { key: 'internal', ready: false },
  { key: 'dental', ready: true },
];
