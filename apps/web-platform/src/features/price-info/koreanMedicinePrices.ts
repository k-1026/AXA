// 자동 생성: data/etl/korean_medicine_price_stats.py → data/processed/daegu_korean_medicine_price_stats.csv
// 심평원 누리집 비급여 진료비 정보 (대구 전체 내려받기), 공개기준 2026-08 · 대구 한의원·한방병원 기관별 최저 금액의 하위 10% ~ 상위 10%
// 내국인 기준 공개 금액 → 외국인 실제 진료비와 다를 수 있음 (가격 가이드 공통 고지)
export const KMED_PRICE_DATE = '2026-08';
export const KMED_PRICES: Record<string, { min: number; max: number; clinics: number }> = {
  '단순추나': { min: 12000, max: 30000, clinics: 255 },
  '복잡추나': { min: 30000, max: 50000, clinics: 174 },
  '특수추나': { min: 30000, max: 80000, clinics: 61 },
  '약침술': { min: 3000, max: 20000, clinics: 600 },
  '경근간섭저주파요법': { min: 200, max: 10000, clinics: 96 },
  '경피전기자극요법': { min: 1000, max: 5220, clinics: 37 },
  '경피온열검사': { min: 10000, max: 100000, clinics: 44 },
  '사상체질검사': { min: 10000, max: 45000, clinics: 27 },
  '한방 향기요법': { min: 1000, max: 50000, clinics: 24 },
};
