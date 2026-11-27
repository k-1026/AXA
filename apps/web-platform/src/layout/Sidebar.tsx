import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useNotifications } from '../features/notifications/NotificationsProvider';

const NAV_ITEMS = [
  { to: '/', key: 'main' },
  { to: '/hospitals', key: 'hospitals' },
  { to: '/prices', key: 'prices' },
  { to: '/chatbot', key: 'chatbot' },
  { to: '/booking', key: 'booking' },
  { to: '/aftercare', key: 'aftercare' },
  { to: '/mypage', key: 'mypage' },
  { to: '/guide', key: 'guide' }, // 가이드북: 이용 방법 (로그인 없이)
] as const;

export function Sidebar() {
  const { t } = useTranslation();
  const { countFor } = useNotifications();
  // 메뉴 옆 새 알림 수: 상담·예약 = 상태 바뀜 + 병원 답장, 사후 관리 = 병원 메시지
  const badge = (key: string) => (key === 'booking' ? countFor('/booking') + countFor('/mypage/bookings') : key === 'aftercare' ? countFor('/aftercare') : 0);

  return (
    <nav className="sidebar" aria-label={t('nav.title')}>
      <p className="sidebar-title">{t('nav.title')}</p>
      <ul>
        {NAV_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink to={item.to} end={item.to === '/'}>
              {t(`nav.${item.key}`)}
              {badge(item.key) > 0 && (
                <span className="nav-badge" aria-label={t('notify.newCount', { count: badge(item.key) })}>
                  {badge(item.key)}
                </span>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
