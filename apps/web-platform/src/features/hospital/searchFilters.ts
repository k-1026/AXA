import { DEPARTMENTS, DISTRICTS } from './filters';
import { SUPPORT_LANGS, supportsAny, type SupportLang } from './languageSupport';
import type { DepartmentKey, Hospital } from './types';

// 병원 찾기 필터 조건
// - 같은 필터 안은 OR, 필터끼리는 AND, 빈 필터는 제한 없음
// - 지역이 비어 있으면 '대구 전체'
export interface SearchFilters {
  depts: DepartmentKey[];
  districts: string[];
  langs: SupportLang[];
}

export const EMPTY_FILTERS: SearchFilters = { depts: [], districts: [], langs: [] };

/** 시연 예시: 피부과·성형외과 / 수성구·중구 / 영어 */
export const DEMO_FILTERS: SearchFilters = {
  depts: ['dermatology', 'plastic'],
  districts: ['수성구', '중구'],
  langs: ['en'],
};

export function matches(h: Hospital, f: SearchFilters): boolean {
  if (f.depts.length && !f.depts.some((d) => h.depts.includes(d))) return false;
  if (f.districts.length && !f.districts.includes(h.district)) return false;
  if (f.langs.length && !supportsAny(h.id, f.langs)) return false;
  return true;
}

/** 중복 id를 빼고 센다 */
export function countMatches(items: Hospital[], f: SearchFilters): number {
  const ids = new Set<string>();
  for (const h of items) if (matches(h, f)) ids.add(h.id);
  return ids.size;
}

export const filterCount = (f: SearchFilters) => f.depts.length + f.districts.length + f.langs.length;

export const sameFilters = (a: SearchFilters, b: SearchFilters) =>
  (['depts', 'districts', 'langs'] as const).every(
    (k) => a[k].length === b[k].length && a[k].every((v) => (b[k] as string[]).includes(v)),
  );

// 주소(?dept=a,b&district=중구,수성구&lang=en) ↔ 조건. 모르는 값은 버림 (빈 목록이 되지 않게)
const list = <T extends string>(raw: string | null, allowed: readonly T[]): T[] =>
  raw ? [...new Set(raw.split(','))].filter((v): v is T => (allowed as readonly string[]).includes(v)) : [];

export function readFilters(params: URLSearchParams): SearchFilters {
  return {
    depts: list(params.get('dept'), DEPARTMENTS),
    districts: list(params.get('district'), DISTRICTS),
    langs: list(params.get('lang'), SUPPORT_LANGS),
  };
}

export function writeFilters(params: URLSearchParams, f: SearchFilters): URLSearchParams {
  const next = new URLSearchParams(params);
  const put = (key: string, values: string[]) => (values.length ? next.set(key, values.join(',')) : next.delete(key));
  put('dept', f.depts);
  put('district', f.districts);
  put('lang', f.langs);
  return next;
}
