import type { DepartmentKey } from './types';

export const DEPARTMENTS: DepartmentKey[] = ['dermatology', 'plastic', 'internal', 'ophthalmology', 'korean_medicine', 'other'];

// 메인 지도에 보이는 진료과 (서비스 5개, 한방 2026-11-23 추가). 치과 등 '기타'만 있는 병원은 지도에서 뺌 (병원 정보 목록에는 그대로)
export const MAP_DEPARTMENTS: DepartmentKey[] = ['dermatology', 'plastic', 'internal', 'ophthalmology', 'korean_medicine'];
export const onMap = (h: { depts: DepartmentKey[] }) => h.depts.some((d) => MAP_DEPARTMENTS.includes(d));

// 지도 점 색상
export const DEPARTMENT_COLORS: Record<DepartmentKey, string> = {
  dermatology: '#ec4899',
  plastic: '#8b5cf6',
  internal: '#facc15',
  ophthalmology: '#2563eb',
  korean_medicine: '#16a34a',
  other: '#64748b',
};

// 데이터의 구·군 이름 (2023년 대구 편입된 군위군 포함)
export const DISTRICTS = ['중구', '동구', '서구', '남구', '북구', '수성구', '달서구', '달성군', '군위군'];
