import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LANGUAGES } from '../i18n';
import { CURRENCIES, useCurrency, type Currency } from '../components/currency';
import { useAuth } from '../components/auth';
import { NotificationBell } from '../features/notifications/NotificationBell';
import { Logo } from '../components/Logo';

export function Header() {
  const { t, i18n } = useTranslation();
  const { currency, setCurrency } = useCurrency();
  const { user, logout } = useAuth();
  const location = useLocation();
  const here = location.pathname;

  return (
    <header className="site-header">
      <div className="brand-wrap">
        <Link to="/" className="brand" aria-label="MediDaegu">
          <Logo />
        </Link>
        {/* 캐치프레이즈 (2026-11 팀 확정, 화면 언어별) */}
        <p className="brand-tagline">{t('header.tagline')}</p>
      </div>
      <div className="header-actions">
        <label className="header-select">
          <span className="visually-hidden">{t('header.language')}</span>
          <select value={i18n.language} onChange={(e) => i18n.changeLanguage(e.target.value)}>
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
        </label>
        <label className="header-select">
          <span className="visually-hidden">{t('header.currency')}</span>
          <select value={currency} onChange={(e) => setCurrency(e.target.value as Currency)}>
            {CURRENCIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        {user && !user.demo && <NotificationBell />}
        {user ? (
          <button type="button" className="header-button" onClick={logout}>
            {t('auth.logout')}
          </button>
        ) : (
          // 로그인 뒤 지금 보던 페이지로 돌아오게 (로그인 화면에서 누르면 그대로)
          <Link to="/login" state={here === '/login' ? location.state : { from: here + location.search }} className="header-button">
            {t('header.login')}
          </Link>
        )}
      </div>
    </header>
  );
}
