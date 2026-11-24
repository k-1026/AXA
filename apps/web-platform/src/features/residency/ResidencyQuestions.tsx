import { useTranslation } from 'react-i18next';

// 체류 형태 3문항 + 거주국 (docs/backend-contracts.md 6-6절, 결정 28)
// 하나라도 해당하거나 거주국이 한국이면 국내 거주 → 정보 열람만 (의료법 제27조 제3항 제2호)
// 가입 화면 · 예약 화면(답이 없는 기존 계정) · 마이페이지(다시 답하기)에서 같이 씀
export interface ResidencyAnswers {
  country: string; // ISO 3166-1 alpha-2
  alien_registration: boolean; // ① 외국인등록 (G-1 제외)
  domestic_residence: boolean; // ② 국내거소신고 (외국국적동포)
  health_insurance: boolean; // ③ 국민건강보험 가입자·피부양자
}

export type Residency = 'short_term' | 'resident';

const COUNTRIES = ['TW', 'CN', 'HK', 'VN', 'JP', 'MN', 'TH', 'PH', 'SG', 'MY', 'KZ', 'RU', 'US', 'GB', 'AU', 'KR'];
const QUESTIONS = ['alien_registration', 'domestic_residence', 'health_insurance'] as const;

export const emptyResidency = (): ResidencyAnswers => ({
  country: 'TW',
  alien_registration: false,
  domestic_residence: false,
  health_insurance: false,
});

// 서버와 같은 규칙 (backend/src/modules/patient/schemas.py ResidencyIn.residency) — 화면 안내용, 판단은 서버
export const residencyOf = (a: ResidencyAnswers): Residency =>
  a.country === 'KR' || a.alien_registration || a.domestic_residence || a.health_insurance ? 'resident' : 'short_term';

export function ResidencyQuestions({ value, onChange }: { value: ResidencyAnswers; onChange: (v: ResidencyAnswers) => void }) {
  const { t, i18n } = useTranslation();
  let names: Intl.DisplayNames | null = null;
  try {
    names = new Intl.DisplayNames([i18n.language], { type: 'region' });
  } catch {
    names = null;
  }
  const set = <K extends keyof ResidencyAnswers>(k: K, v: ResidencyAnswers[K]) => onChange({ ...value, [k]: v });

  return (
    <fieldset className="residency-questions">
      <legend>{t('residency.title')}</legend>
      <label className="auth-field">
        <span>{t('residency.country')}</span>
        <select value={value.country} onChange={(e) => set('country', e.target.value)}>
          {COUNTRIES.map((c) => (
            <option key={c} value={c}>
              {names?.of(c) ?? c}
            </option>
          ))}
        </select>
      </label>
      <p className="residency-intro">{t('residency.intro')}</p>
      {QUESTIONS.map((q) => (
        <label key={q} className="auth-check">
          <input type="checkbox" checked={value[q]} onChange={(e) => set(q, e.target.checked)} />
          <span>{t(`residency.q.${q}`)}</span>
        </label>
      ))}
      {residencyOf(value) === 'resident' && (
        <p className="residency-note" role="status">
          {t('residency.residentNote')}
        </p>
      )}
    </fieldset>
  );
}
