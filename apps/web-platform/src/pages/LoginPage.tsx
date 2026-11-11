import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../components/auth';

// 회원 로그인은 준비 중. 발표·화면 확인용 데모 계정으로만 들어갈 수 있다
export function LoginPage() {
  const { t } = useTranslation();
  const { user, loginDemo, logout } = useAuth();
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? '/mypage';

  const startDemo = () => {
    loginDemo();
    navigate(from, { replace: true });
  };

  return (
    <section className="mp-card mp-login-required">
      <h1>{t('header.login')}</h1>
      {user ? (
        <>
          <p>{t('auth.loggedInAs', { name: user.name })}</p>
          <div className="mp-login-actions">
            <Link to="/mypage" className="mp-login-button">
              {t('nav.mypage')}
            </Link>
            <button type="button" className="mp-login-secondary" onClick={logout}>
              {t('auth.logout')}
            </button>
          </div>
        </>
      ) : (
        <>
          <p>{t('auth.comingSoon')}</p>
          <button type="button" className="mp-login-button" onClick={startDemo}>
            {t('auth.demo')}
          </button>
          <p className="mp-login-note">{t('auth.demoNote')}</p>
        </>
      )}
    </section>
  );
}
