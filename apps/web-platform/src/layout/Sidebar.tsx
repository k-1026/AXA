import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const NAV_ITEMS = [
  { to: '/', key: 'main' },
  { to: '/hospitals', key: 'hospitals' },
  { to: '/prices', key: 'prices' },
  { to: '/chatbot', key: 'chatbot' },
  { to: '/booking', key: 'booking' },
  { to: '/aftercare', key: 'aftercare' },
  { to: '/mypage', key: 'mypage' },
] as const;

export function Sidebar() {
  const { t } = useTranslation();

  return (
    <nav className="sidebar" aria-label={t('nav.title')}>
      <p className="sidebar-title">{t('nav.title')}</p>
      <ul>
        {NAV_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink to={item.to} end={item.to === '/'}>
              {t(`nav.${item.key}`)}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
