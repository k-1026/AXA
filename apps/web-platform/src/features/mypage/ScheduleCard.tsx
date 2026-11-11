import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { CalendarIcon, DaeguSkyline, PencilIcon, PlusIcon } from './icons';
import { ScheduleEntry } from './ScheduleEntry';
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
  const fmt = new Intl.DateTimeFormat(lang, { month: 'long', day: 'numeric', timeZone: 'Asia/Seoul' });
  return (fmt as RangeFormat).formatRange(new Date(`${start}T00:00:00+09:00`), new Date(`${end}T00:00:00+09:00`));
}

export function ScheduleCard({ start, end, items }: Props) {
  const { t, i18n } = useTranslation();

  return (
    <section className="mp-card mp-schedule" aria-labelledby="mp-schedule-title">
      <DaeguSkyline />
      <div className="mp-card-head">
        <h2 id="mp-schedule-title">{t('mypage.schedule.title')}</h2>
        <Link to="/mypage/schedule" className="mp-text-link">
          <PencilIcon />
          {t('mypage.schedule.edit')}
        </Link>
      </div>
      {/* 실제 회원은 여행 기간이 아직 없음 (빈 날짜로 formatRange하면 오류) */}
      {start && end && (
        <p className="mp-trip-range">
          <CalendarIcon />
          {formatRange(start, end, i18n.language)}
        </p>
      )}
      <ol className="mp-timeline">
        {items.map((item) => (
          <ScheduleEntry key={item.id} item={item} />
        ))}
      </ol>
      <Link to="/mypage/schedule" className="mp-text-link mp-add">
        <PlusIcon />
        {t('mypage.schedule.add')}
      </Link>
    </section>
  );
}
