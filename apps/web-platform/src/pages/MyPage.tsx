import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { StatCard } from '../features/mypage/StatCard';
import { ScheduleCard } from '../features/mypage/ScheduleCard';
import { ChecklistCard } from '../features/mypage/ChecklistCard';
import { AccountBar } from '../features/mypage/AccountBar';
import { LegalLinks } from '../features/legal/LegalLinks';
import { CalendarCheckIcon, CalendarIcon, ClockIcon, HospitalHeartIcon } from '../features/mypage/icons';
import { useConsultThreads } from '../features/consult/useConsultThreads';
import { displayStatus, type DisplayStatus } from '../features/consult/types';

const ACTIVE = new Set<DisplayStatus>(['pending', 'proposed', 'confirmed']);
import { useMyPageData } from '../features/mypage/useMyPageData';

// 로그인 후 마이페이지. 데모 계정은 예시 데이터로 표시
export function MyPage() {
  const { t } = useTranslation();
  const { data, demo } = useMyPageData();
  // 예약 관리 카드 숫자 = 진행 중인 예약 (확인 대기·다른 시간 제안·확정). 회원은 서버 예약, 데모는 예시 상담
  const { bookings } = useConsultThreads();
  const activeBookings = bookings.filter((b) => ACTIVE.has(displayStatus(b.booking))).length;

  return (
    <div className="mypage">
      <nav className="mp-breadcrumb" aria-label="breadcrumb">
        <Link to="/">{t('mypage.home')}</Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{t('nav.mypage')}</span>
      </nav>

      <div className="mp-title-row">
        <h1>
          {t('nav.mypage')}
          {demo && <span className="mp-demo-badge">{t('auth.demoBadge')}</span>}
        </h1>
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
        <StatCard to="/mypage/bookings" label={t('mypage.stats.bookings')} value={activeBookings} icon={<CalendarIcon />} tone="green" />
      </div>

      <div className="mp-main-row">
        <ScheduleCard start={data.trip.start} end={data.trip.end} items={data.schedule} />
        <ChecklistCard initial={data.checklist} />
      </div>

      <AccountBar />
      <LegalLinks />
    </div>
  );
}
