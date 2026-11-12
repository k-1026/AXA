import { useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../components/auth';
import { ApiError } from '../components/api';
import { LANGUAGES } from '../i18n';
import { TERMS } from '../features/legal/terms';
import { PRIVACY } from '../features/legal/privacy';

// 로그인·회원가입. 실제 계정은 백엔드에, 데모 계정은 발표·화면 확인용으로 아래에 남겨 둠
const PASSWORD_MIN = 8; // 백엔드 규칙과 같음 (backend/src/modules/auth/schemas.py)

// 해외 환자 주요 국가 + 한국. 브라우저 시간대가 목록에 없으면 맨 위에 추가
const TIMEZONES = [
  'Asia/Seoul',
  'Asia/Taipei',
  'Asia/Shanghai',
  'Asia/Hong_Kong',
  'Asia/Ho_Chi_Minh',
  'Asia/Tokyo',
  'Asia/Bangkok',
  'Asia/Singapore',
  'Asia/Ulaanbaatar',
  'Asia/Almaty',
  'Europe/Moscow',
  'Europe/London',
  'America/New_York',
  'America/Los_Angeles',
  'Australia/Sydney',
  'UTC',
];

function browserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Seoul';
  } catch {
    return 'Asia/Seoul';
  }
}

type Mode = 'login' | 'signup';

export function LoginPage() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const [mode, setMode] = useState<Mode>('login');

  if (user) {
    return (
      <section className="mp-card mp-login-required">
        <h1>{t('header.login')}</h1>
        <p>{t('auth.loggedInAs', { name: user.name })}</p>
        <div className="mp-login-actions">
          <Link to="/mypage" className="mp-login-button">
            {t('nav.mypage')}
          </Link>
          <button type="button" className="mp-login-secondary" onClick={logout}>
            {t('auth.logout')}
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="mp-card auth-card">
      <div className="auth-tabs" role="tablist">
        {(['login', 'signup'] as const).map((m) => (
          <button
            key={m}
            type="button"
            role="tab"
            aria-selected={mode === m}
            className={mode === m ? 'auth-tab active' : 'auth-tab'}
            onClick={() => setMode(m)}
          >
            {t(m === 'login' ? 'auth.tabLogin' : 'auth.tabSignup')}
          </button>
        ))}
      </div>
      {mode === 'login' ? <LoginForm /> : <SignupForm />}
      <DemoEntry />
    </section>
  );
}

function useAfterLogin() {
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? '/mypage';
  return () => navigate(from, { replace: true });
}

function errorKey(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.code === 'auth.invalid_credentials') return 'auth.err.invalidCredentials';
    if (e.code === 'auth.email_taken') return 'auth.err.emailTaken';
    if (e.code === 'consent.required') return 'auth.err.consent';
    if (e.code === 'validation') return 'auth.err.validation';
    if (e.code === 'network') return 'auth.err.network';
  }
  return 'auth.err.unknown';
}

function LoginForm() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const done = useAfterLogin();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email.trim(), password);
      done();
    } catch (err) {
      setError(errorKey(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="auth-form" onSubmit={submit} noValidate>
      <label className="auth-field">
        <span>{t('auth.email')}</span>
        <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label className="auth-field">
        <span>{t('auth.password')}</span>
        <input
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>
      {error && (
        <p className="auth-error" role="alert">
          {t(error)}
        </p>
      )}
      <button type="submit" className="mp-login-button auth-submit" disabled={busy || !email || !password}>
        {busy ? t('auth.submitting') : t('auth.submitLogin')}
      </button>
    </form>
  );
}

function SignupForm() {
  const { t, i18n } = useTranslation();
  const { signup } = useAuth();
  const done = useAfterLogin();
  const tzDefault = browserTimezone();
  const zones = TIMEZONES.includes(tzDefault) ? TIMEZONES : [tzDefault, ...TIMEZONES];

  const [f, setF] = useState({
    email: '',
    password: '',
    confirm: '',
    displayName: '',
    lang: i18n.language,
    timezone: tzDefault,
    age14: false,
    terms: false,
    privacy: false,
  });
  const set = <K extends keyof typeof f>(k: K, v: (typeof f)[K]) => setF((p) => ({ ...p, [k]: v }));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const shortPw = f.password.length > 0 && f.password.length < PASSWORD_MIN;
  const mismatch = f.confirm.length > 0 && f.password !== f.confirm;
  const allAgreed = f.age14 && f.terms && f.privacy;
  const canSubmit =
    !!f.email && f.password.length >= PASSWORD_MIN && f.password === f.confirm && allAgreed && !busy;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setError(null);
    setBusy(true);
    try {
      await signup({
        email: f.email.trim(),
        password: f.password,
        display_name: f.displayName.trim() || null,
        preferred_lang: f.lang,
        timezone: f.timezone,
        age14_confirmed: f.age14,
        // 동의 문구 버전 = 화면에 보여준 문서의 개정일
        consents: [
          { kind: 'terms', version: TERMS.updated },
          { kind: 'privacy', version: PRIVACY.updated },
        ],
      });
      done();
    } catch (err) {
      setError(errorKey(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="auth-form" onSubmit={submit} noValidate>
      <label className="auth-field">
        <span>{t('auth.email')}</span>
        <input type="email" autoComplete="email" required value={f.email} onChange={(e) => set('email', e.target.value)} />
      </label>
      <label className="auth-field">
        <span>{t('auth.password')}</span>
        <input
          type="password"
          autoComplete="new-password"
          required
          minLength={PASSWORD_MIN}
          maxLength={128}
          value={f.password}
          onChange={(e) => set('password', e.target.value)}
          aria-invalid={shortPw}
        />
        <small className={shortPw ? 'auth-hint bad' : 'auth-hint'}>{t('auth.passwordHint', { n: PASSWORD_MIN })}</small>
      </label>
      <label className="auth-field">
        <span>{t('auth.passwordConfirm')}</span>
        <input
          type="password"
          autoComplete="new-password"
          required
          value={f.confirm}
          onChange={(e) => set('confirm', e.target.value)}
          aria-invalid={mismatch}
        />
        {mismatch && <small className="auth-hint bad">{t('auth.passwordMismatch')}</small>}
      </label>
      <label className="auth-field">
        <span>
          {t('auth.displayName')} <em>{t('auth.optional')}</em>
        </span>
        <input
          type="text"
          autoComplete="nickname"
          maxLength={30}
          value={f.displayName}
          onChange={(e) => set('displayName', e.target.value)}
        />
        <small className="auth-hint">{t('auth.displayNameHint')}</small>
      </label>
      <div className="auth-row">
        <label className="auth-field">
          <span>{t('auth.language')}</span>
          <select value={f.lang} onChange={(e) => set('lang', e.target.value)}>
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
        </label>
        <label className="auth-field">
          <span>{t('auth.timezone')}</span>
          <select value={f.timezone} onChange={(e) => set('timezone', e.target.value)}>
            {zones.map((z) => (
              <option key={z} value={z}>
                {z.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </label>
      </div>

      <fieldset className="auth-consents">
        <legend>{t('auth.consentsTitle')}</legend>
        <label className="auth-check">
          <input type="checkbox" checked={f.age14} onChange={(e) => set('age14', e.target.checked)} />
          <span>{t('auth.age14')}</span>
        </label>
        <label className="auth-check">
          <input type="checkbox" checked={f.terms} onChange={(e) => set('terms', e.target.checked)} />
          <span>
            {t('auth.agreeTerms')}{' '}
            <Link to="/legal/terms" target="_blank" rel="noopener">
              {t('auth.viewDoc')}
            </Link>
          </span>
        </label>
        <label className="auth-check">
          <input type="checkbox" checked={f.privacy} onChange={(e) => set('privacy', e.target.checked)} />
          <span>
            {t('auth.agreePrivacy')}{' '}
            <Link to="/legal/privacy" target="_blank" rel="noopener">
              {t('auth.viewDoc')}
            </Link>
          </span>
        </label>
      </fieldset>

      {error && (
        <p className="auth-error" role="alert">
          {t(error)}
        </p>
      )}
      <button type="submit" className="mp-login-button auth-submit" disabled={!canSubmit}>
        {busy ? t('auth.submitting') : t('auth.submitSignup')}
      </button>
    </form>
  );
}

function DemoEntry() {
  const { t } = useTranslation();
  const { loginDemo } = useAuth();
  const done = useAfterLogin();
  return (
    <div className="auth-demo">
      <button
        type="button"
        className="mp-login-secondary"
        onClick={() => {
          loginDemo();
          done();
        }}
      >
        {t('auth.demo')}
      </button>
      <p className="mp-login-note">{t('auth.demoNote')}</p>
    </div>
  );
}
