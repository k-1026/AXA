import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { StatCard } from '../features/mypage/StatCard';
import { ScheduleCard } from '../features/mypage/ScheduleCard';
import { ChecklistCard } from '../features/mypage/ChecklistCard';
import { AccountBar } from '../features/mypage/AccountBar';
import { CalendarCheckIcon, ClockIcon, HistoryIcon, HospitalHeartIcon } from '../features/mypage/icons';
import { SAMPLE_MYPAGE } from '../features/mypage/sampleData';

// 로그인 후 마이페이지. 지금은 예시 데이터로 표시
export function MyPage() {
  const { t } = useTranslation();
  const data = SAMPLE_MYPAGE;

  return (
    <div className="mypage">
      <nav className="mp-breadcrumb" aria-label="breadcrumb">
        <Link to="/">{t('mypage.home')}</Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{t('nav.mypage')}</span>
      </nav>

      <div className="mp-title-row">
        <h1>{t('nav.mypage')}</h1>
        <span className="mp-kst">
          <ClockIcon />
          {t('mypage.kst')}
        </span>
      </div>

      <div className="mp-greeting">
        <p className="mp-greeting-title">{t('mypage.greeting', { name: data.user.name })}</p>
        <p className="mp-greeting-sub">{t('mypage.subtitle')}</p>
      </div>

      <div className="mp-stats">
        <StatCard to="/mypage/saved" label={t('mypage.stats.saved')} value={data.stats.saved} icon={<HospitalHeartIcon />} tone="blue" />
        <StatCard to="/mypage/visits" label={t('mypage.stats.visits')} value={data.stats.visits} icon={<CalendarCheckIcon />} tone="orange" />
        <StatCard to="/mypage/recent" label={t('mypage.stats.recent')} value={data.stats.recent} icon={<HistoryIcon />} tone="green" />
      </div>

      <div className="mp-main-row">
        <ScheduleCard start={data.trip.start} end={data.trip.end} items={data.schedule} />
        <ChecklistCard initial={data.checklist} />
      </div>

      <AccountBar />
    </div>
  );
}
