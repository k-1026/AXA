import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api, API_BASE, ApiError } from '../../components/api';
import { PRIVACY } from '../legal/privacy';
import { TERMS } from '../legal/terms';

// 병원 관계자(입점 병원) 가입·로그인. 환자 계정과 따로 (가입할 때 나눔, docs/backend-contracts.md 3절)
// 성공하면 직원 토큰을 들고 병원 대시보드로 이동 (?token=&api=). 대시보드는 읽자마자 주소에서 지우고 그 탭에만 보관하며,
// 대시보드 자체 로그인 창도 있음 (docs/dashboard-integration.md "시연용 대시보드 연결")
const PASSWORD_MIN = 8;
const REG_NO = /^M-\d{4}-\d{2}-\d{2}-\d{4,6}$/;

interface HospitalOption {
  id: number;
  name_ko: string;
  sggu: string | null;
  can_request: boolean;
}

function goDashboard(token: string): string | null {
  const base = import.meta.env.VITE_DASHBOARD_URL;
  if (!base) return null;
  const url = `${base}${base.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}&api=${encodeURIComponent(API_BASE)}`;
  window.location.assign(url);
  return url;
}

function errorKey(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.code === 'auth.invalid_credentials') return 'auth.err.invalidCredentials';
    if (e.code === 'auth.email_taken') return 'auth.err.emailTaken';
    if (e.code === 'auth.hospital_taken') return 'staff.err.hospitalTaken';
    if (e.code === 'hospital.not_requestable') return 'staff.err.notRegistered';
    if (e.code === 'auth.too_many_attempts') return 'staff.err.tooMany';
    if (e.code === 'consent.required') return 'auth.err.consent';
    if (e.code === 'validation') return 'auth.err.validation';
    if (e.code === 'network') return 'auth.err.network';
  }
  return 'auth.err.unknown';
}

// 대시보드 주소가 없을 때(로컬 등) 보여 주는 완료 화면
function Done() {
  const { t } = useTranslation();
  return (
    <div className="auth-form">
      <p className="auth-hint">{t('staff.doneNoDashboard')}</p>
    </div>
  );
}

export function StaffLoginForm() {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const r = await api<{ access_token: string }>('/auth/staff/login', { method: 'POST', body: { email: email.trim(), password } });
      if (!goDashboard(r.access_token)) setDone(true);
    } catch (err) {
      setError(errorKey(err));
    } finally {
      setBusy(false);
    }
  };

  if (done) return <Done />;
  return (
    <form className="auth-form" onSubmit={submit} noValidate>
      <label className="auth-field">
        <span>{t('staff.email')}</span>
        <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label className="auth-field">
        <span>{t('auth.password')}</span>
        <input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
      </label>
      {error && <p className="auth-error" role="alert">{t(error)}</p>}
      <button type="submit" className="mp-login-button auth-submit" disabled={busy || !email || !password}>
        {busy ? t('auth.submitting') : t('staff.submitLogin')}
      </button>
    </form>
  );
}

export function StaffSignupForm() {
  const { t } = useTranslation();
  const [hospitals, setHospitals] = useState<HospitalOption[] | null>(null);
  const [f, setF] = useState({ email: '', password: '', confirm: '', hospitalId: '', regNo: '', terms: false, privacy: false });
  const set = <K extends keyof typeof f>(k: K, v: (typeof f)[K]) => setF((p) => ({ ...p, [k]: v }));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  // 입점은 등록 외국인환자 유치의료기관만 (영업 중인 곳)
  useEffect(() => {
    api<HospitalOption[]>('/hospitals?registered=true&sort=name')
      .then((list) => setHospitals(list.filter((h) => h.can_request)))
      .catch(() => setHospitals([]));
  }, []);

  const shortPw = f.password.length > 0 && f.password.length < PASSWORD_MIN;
  const mismatch = f.confirm.length > 0 && f.password !== f.confirm;
  const badReg = f.regNo.length > 0 && !REG_NO.test(f.regNo.trim());
  const canSubmit =
    !!f.email && f.password.length >= PASSWORD_MIN && f.password === f.confirm && !!f.hospitalId && REG_NO.test(f.regNo.trim()) && f.terms && f.privacy && !busy;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setError(null);
    setBusy(true);
    try {
      const r = await api<{ access_token: string }>('/auth/staff/signup', {
        method: 'POST',
        body: {
          email: f.email.trim(),
          password: f.password,
          hospital_id: Number(f.hospitalId),
          registration_no: f.regNo.trim(),
          consents: [
            { kind: 'terms', version: TERMS.updated },
            { kind: 'privacy', version: PRIVACY.updated },
          ],
        },
      });
      if (!goDashboard(r.access_token)) setDone(true);
    } catch (err) {
      setError(errorKey(err));
    } finally {
      setBusy(false);
    }
  };

  if (done) return <Done />;
  return (
    <form className="auth-form" onSubmit={submit} noValidate>
      <p className="auth-hint">{t('staff.signupIntro')}</p>
      <label className="auth-field">
        <span>{t('staff.hospital')}</span>
        <select value={f.hospitalId} onChange={(e) => set('hospitalId', e.target.value)} disabled={!hospitals}>
          <option value="">{hospitals ? t('staff.pickHospital') : t('auth.submitting')}</option>
          {hospitals?.map((h) => (
            <option key={h.id} value={h.id}>
              {h.name_ko}
              {h.sggu ? ` (${h.sggu.replace('대구', '')})` : ''}
            </option>
          ))}
        </select>
      </label>
      <label className="auth-field">
        <span>{t('staff.regNo')}</span>
        <input type="text" placeholder="M-2009-03-01-0013" value={f.regNo} onChange={(e) => set('regNo', e.target.value)} aria-invalid={badReg} />
        <small className={badReg ? 'auth-hint bad' : 'auth-hint'}>{t('staff.regNoHint')}</small>
      </label>
      <label className="auth-field">
        <span>{t('staff.email')}</span>
        <input type="email" autoComplete="email" required value={f.email} onChange={(e) => set('email', e.target.value)} />
      </label>
      <label className="auth-field">
        <span>{t('auth.password')}</span>
        <input type="password" autoComplete="new-password" value={f.password} onChange={(e) => set('password', e.target.value)} aria-invalid={shortPw} />
        <small className={shortPw ? 'auth-hint bad' : 'auth-hint'}>{t('auth.passwordHint', { n: PASSWORD_MIN })}</small>
      </label>
      <label className="auth-field">
        <span>{t('auth.passwordConfirm')}</span>
        <input type="password" autoComplete="new-password" value={f.confirm} onChange={(e) => set('confirm', e.target.value)} aria-invalid={mismatch} />
        {mismatch && <small className="auth-hint bad">{t('auth.passwordMismatch')}</small>}
      </label>
      <fieldset className="auth-consents">
        <legend>{t('auth.consentsTitle')}</legend>
        <label className="auth-check">
          <input type="checkbox" checked={f.terms} onChange={(e) => set('terms', e.target.checked)} />
          <span>
            {t('auth.agreeTerms')}{' '}
            <Link to="/legal/terms" target="_blank" rel="noopener">{t('auth.viewDoc')}</Link>
          </span>
        </label>
        <label className="auth-check">
          <input type="checkbox" checked={f.privacy} onChange={(e) => set('privacy', e.target.checked)} />
          <span>
            {t('auth.agreePrivacy')}{' '}
            <Link to="/legal/privacy" target="_blank" rel="noopener">{t('auth.viewDoc')}</Link>
          </span>
        </label>
      </fieldset>
      {error && <p className="auth-error" role="alert">{t(error)}</p>}
      <button type="submit" className="mp-login-button auth-submit" disabled={!canSubmit}>
        {busy ? t('auth.submitting') : t('staff.submitSignup')}
      </button>
    </form>
  );
}
