import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { CalendarIcon, DaeguSkyline } from './icons';
import { ScheduleEntry } from './ScheduleEntry';
import { KST } from '../../lib/common';
import type { ScheduleItem } from './sampleData';

interface Props {
  start: string;
  end: string;
  items: ScheduleItem[];
}

// 여행 기간 표시: 언어별 날짜 형식 (예: 11월 20일 – 22일, Nov 20 – 22)
// formatRange는 ES2021 타입이라 tsconfig(ES2020)에 맞춰 타입만 보강
type RangeFormat = Intl.DateTimeFormat & { formatRange(a: Date, b: Date): string };

function formatRange(start: string, end: string, lang: string) {
  const fmt = new Intl.DateTimeFormat(lang, { month: 'long', day: 'numeric', timeZone: KST });
  return (fmt as RangeFormat).formatRange(new Date(`${start}T00:00:00+09:00`), new Date(`${end}T00:00:00+09:00`));
}

export function ScheduleCard({ start, end, items }: Props) {
  const { t, i18n } = useTranslation();

  return (
    <section className="mp-card mp-schedule" aria-labelledby="mp-schedule-title">
      <DaeguSkyline />
      {/* 일정 수정·추가 화면(/mypage/schedule)은 아직 없음 → 링크를 숨김. 일정 편집 기능이 생기면 다시 붙이기 */}
      <div className="mp-card-head">
        <h2 id="mp-schedule-title">{t('mypage.schedule.title')}</h2>
      </div>
      {/* 실제 회원은 여행 기간이 아직 없음 (빈 날짜로 formatRange하면 오류) */}
      {start && end && (
        <p className="mp-trip-range">
          <CalendarIcon />
          {formatRange(start, end, i18n.language)}
        </p>
      )}
      {items.length > 0 ? (
        <ol className="mp-timeline">
          {items.map((item) => (
            <ScheduleEntry key={item.id} item={item} />
          ))}
        </ol>
      ) : (
        <p className="mp-schedule-empty">
          {t('mypage.schedule.empty')}{' '}
          <Link to="/mypage/bookings" className="mp-text-link">
            {t('mypage.stats.bookings')}
          </Link>
        </p>
      )}
    </section>
  );
}
