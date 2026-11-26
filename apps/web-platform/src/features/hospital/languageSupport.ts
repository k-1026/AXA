// 병원별 진료·상담 언어
// - 공공데이터(심평원·메디컬코리아)에는 응대 언어 항목이 없음 → 실제 병원은 "정보 없음"이고, 언어 필터에서 지원 병원으로 치지 않음
// - 아래 값은 **시연용 가상 병원(DEMO-…)의 예시 데이터**. 직접 소통 언어는 data/processed/demo/demo_hospitals.json의
//   staff_languages + 한국어, 통역 지원은 시연을 위한 예시값
// - 입점 병원이 대시보드 '병원 설정'에서 입력하면 그 값으로 바꾼다

export const SUPPORT_LANGS = ['ko', 'en', 'ja', 'zh', 'vi', 'ru'] as const;
export type SupportLang = (typeof SUPPORT_LANGS)[number];

export interface LanguageSupport {
  /** 의료진·직원과 그 언어로 바로 대화 가능 */
  direct: SupportLang[];
  /** 통역사·통역 서비스를 통해 지원 */
  interpret: SupportLang[];
  /** 예시 데이터 여부 (화면에 '예시' 표시) */
  sample: boolean;
}

const SAMPLE_SUPPORT: Record<string, Omit<LanguageSupport, 'sample'>> = {
  'DEMO-9001': { direct: ['ko', 'en', 'zh'], interpret: ['ja'] },
  'DEMO-9002': { direct: ['ko', 'en'], interpret: ['zh'] },
  'DEMO-9003': { direct: ['ko', 'zh', 'vi'], interpret: ['en'] },
  'DEMO-9004': { direct: ['ko', 'en', 'vi'], interpret: [] },
};

export function languageSupportOf(hospitalId: string): LanguageSupport | null {
  const s = SAMPLE_SUPPORT[hospitalId];
  return s ? { ...s, sample: true } : null;
}

/** 언어 정보가 없는 병원은 false (지원 가능으로 보지 않음) */
export function supportsAny(hospitalId: string, langs: SupportLang[]): boolean {
  const s = languageSupportOf(hospitalId);
  if (!s) return false;
  return langs.some((l) => s.direct.includes(l) || s.interpret.includes(l));
}
