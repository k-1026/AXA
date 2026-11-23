import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../components/auth';
import { PRIVACY } from '../legal/privacy';
import { emptyResidency, ResidencyQuestions, type Residency, type ResidencyAnswers } from '../residency/ResidencyQuestions';
import { OVERSEAS_VERSION, type BookingExtra } from './bookingApi';

// 실제 회원이 예약을 요청할 때만 받는 칸 (docs/backend-contracts.md 6절)
// - 체류 형태: 판단은 가입 때 3문항(계정 값, 결정 28). 답이 없는 계정이면 여기서 3문항, 국내 거주면 요청 불가 안내
// - 국적 · 단기 방문 재확인(제출 때 한 번 더, 국내 거주 외국인은 유치 대상 아님, 의료법 제27조 제3항 제2호)
// - 동의: 병원에 요청 내용 전달(privacy) 항상 · 요청 사항을 적으면 번역(해외 AI)용 국외 이전(overseas_transfer)
const COUNTRIES = ['TW', 'CN', 'HK', 'VN', 'JP', 'MN', 'TH', 'PH', 'SG', 'MY', 'KZ', 'RU', 'US', 'GB', 'AU'];

export interface ConsentState {
  nationality: string;
  shortTerm: boolean;
  privacy: boolean;
  overseas: boolean;
  residency: ResidencyAnswers; // 계정에 체류 형태 답이 없을 때만 씀
}

export const emptyConsent = (): ConsentState => ({
  nationality: 'TW',
  shortTerm: false,
  privacy: false,
  overseas: false,
  residency: emptyResidency(),
});

export const consentReady = (c: ConsentState, hasNote: boolean, residency?: Residency | null) =>
  residency !== 'resident' && c.shortTerm && c.privacy && (!hasNote || c.overseas);

// 예약 요청 직전: 계정에 답이 없으면 여기서 받은 3문항을 서버에 저장 (PUT /me/residency), 국내 거주면 멈춤
export function useResidencyCheck() {
  const { user, setResidency } = useAuth();
  return async (c: ConsentState) => {
    const r = user?.residency ?? (await setResidency(c.residency));
    if (r !== 'short_term') throw new Error('residency.not_eligible');
  };
}

export function toExtra(c: ConsentState, hasNote: boolean): BookingExtra {
  return {
    nationality: c.nationality,
    consents: [
      { kind: 'privacy', version: PRIVACY.updated },
      ...(hasNote && c.overseas ? [{ kind: 'overseas_transfer' as const, version: OVERSEAS_VERSION }] : []),
    ],
  };
}

export function BookingConsentFields({ value, onChange, hasNote }: { value: ConsentState; onChange: (v: ConsentState) => void; hasNote: boolean }) {
  const { t, i18n } = useTranslation();
  let names: Intl.DisplayNames | null = null;
  try {
    names = new Intl.DisplayNames([i18n.language], { type: 'region' });
  } catch {
    names = null;
  }
  const residency = useAuth().user?.residency;
  const set = <K extends keyof ConsentState>(k: K, v: ConsentState[K]) => onChange({ ...value, [k]: v });
  if (residency === 'resident') {
    return (
      <p className="residency-blocked" role="alert">
        {t('residency.bookingBlocked')} <Link to="/mypage">{t('residency.editLink')}</Link>
      </p>
    );
  }
  return (
    <fieldset className="booking-consents">
      {residency == null && <ResidencyQuestions value={value.residency} onChange={(v) => set('residency', v)} />}
      <label className="auth-field">
        <span>{t('booking.nationality')}</span>
        <select value={value.nationality} onChange={(e) => set('nationality', e.target.value)}>
          {COUNTRIES.map((c) => (
            <option key={c} value={c}>
              {names?.of(c) ?? c}
            </option>
          ))}
        </select>
      </label>
      <label className="auth-check">
        <input type="checkbox" checked={value.shortTerm} onChange={(e) => set('shortTerm', e.target.checked)} />
        <span>{t('booking.shortTerm')}</span>
      </label>
      <label className="auth-check">
        <input type="checkbox" checked={value.privacy} onChange={(e) => set('privacy', e.target.checked)} />
        <span>
          {t('booking.agreeShare')}{' '}
          <Link to="/legal/privacy" target="_blank" rel="noopener">
            {t('auth.viewDoc')}
          </Link>
        </span>
      </label>
      {hasNote && (
        <label className="auth-check">
          <input type="checkbox" checked={value.overseas} onChange={(e) => set('overseas', e.target.checked)} />
          <span>{t('booking.agreeOverseas')}</span>
        </label>
      )}
    </fieldset>
  );
}
