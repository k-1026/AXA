import type { DepartmentKey } from './types';

export const DEPARTMENTS: DepartmentKey[] = ['dermatology', 'plastic', 'internal', 'ophthalmology'];

// 지도 점 색상
export const DEPARTMENT_COLORS: Record<DepartmentKey, string> = {
  dermatology: '#ec4899',
  plastic: '#8b5cf6',
  internal: '#facc15',
  ophthalmology: '#2563eb',
};

// 데이터의 구·군 이름 (2023년 대구 편입된 군위군 포함)
export const DISTRICTS = ['중구', '동구', '서구', '남구', '북구', '수성구', '달서구', '달성군', '군위군'];
