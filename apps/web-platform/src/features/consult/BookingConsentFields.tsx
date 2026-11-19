import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { PRIVACY } from '../legal/privacy';
import { OVERSEAS_VERSION, type BookingExtra } from './bookingApi';

// 실제 회원이 예약을 요청할 때만 받는 칸 (docs/backend-contracts.md 6절)
// - 국적 · 단기 방문 확인(국내 거주 외국인은 유치 대상 아님, 의료법 제27조 제3항 제2호)
// - 동의: 병원에 요청 내용 전달(privacy) 항상 · 요청 사항을 적으면 번역(해외 AI)용 국외 이전(overseas_transfer)
const COUNTRIES = ['TW', 'CN', 'HK', 'VN', 'JP', 'MN', 'TH', 'PH', 'SG', 'MY', 'KZ', 'RU', 'US', 'GB', 'AU'];

export interface ConsentState {
  nationality: string;
  shortTerm: boolean;
  privacy: boolean;
  overseas: boolean;
}

export const emptyConsent = (): ConsentState => ({ nationality: 'TW', shortTerm: false, privacy: false, overseas: false });

export const consentReady = (c: ConsentState, hasNote: boolean) => c.shortTerm && c.privacy && (!hasNote || c.overseas);

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
  const set = <K extends keyof ConsentState>(k: K, v: ConsentState[K]) => onChange({ ...value, [k]: v });
  return (
    <fieldset className="booking-consents">
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
