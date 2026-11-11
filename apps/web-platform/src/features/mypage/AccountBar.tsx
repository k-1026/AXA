import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowRightIcon, GearIcon } from './icons';

export function AccountBar() {
  const { t } = useTranslation();

  return (
    <section className="mp-card mp-account" aria-labelledby="mp-account-title">
      <GearIcon />
      <h2 id="mp-account-title">{t('mypage.account.title')}</h2>
      <p>{t('mypage.account.desc')}</p>
      <Link to="/mypage/account" className="mp-text-link">
        {t('mypage.account.manage')}
        <ArrowRightIcon />
      </Link>
    </section>
  );
}
