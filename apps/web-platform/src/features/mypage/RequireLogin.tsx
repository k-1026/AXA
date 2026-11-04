import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../components/auth';
import { HospitalHeartIcon } from './icons';

// 마이페이지는 로그인한 사람에게만 보여준다. 로그인 전에는 안내만 표시
export function RequireLogin({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const location = useLocation();

  if (user) return <>{children}</>;

  return (
    <section className="mp-card mp-login-required">
      <span className="mp-stat-icon tone-blue">
        <HospitalHeartIcon />
      </span>
      <h1>{t('auth.requiredTitle')}</h1>
      <p>{t('auth.requiredDesc')}</p>
      <Link to="/login" state={{ from: location.pathname }} className="mp-login-button">
        {t('header.login')}
      </Link>
    </section>
  );
}
