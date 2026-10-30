import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LANGUAGES } from '../i18n';
import { CURRENCIES, useCurrency, type Currency } from '../components/currency';

export function Header() {
  const { t, i18n } = useTranslation();
  const { currency, setCurrency } = useCurrency();

  return (
    <header className="site-header">
      <Link to="/" className="brand">
        MediDaegu
      </Link>
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
        <Link to="/login" className="header-button">
          {t('header.login')}
        </Link>
      </div>
    </header>
  );
}
