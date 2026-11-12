import { useTranslation } from 'react-i18next';
import { ArrowUpRightIcon } from './icons';
import { useLocalized } from '../../lib/common';
import type { ScheduleItem } from './sampleData';

// 병원 방문은 "직접 등록" 표시로 사용자가 넣은 일정임을 보여준다
const TAG_KEY: Record<ScheduleItem['kind'], string> = {
  hospital: 'mypage.schedule.tag.userAdded',
  experience: 'mypage.schedule.tag.experience',
  tour: 'mypage.schedule.tag.tour',
};

export function ScheduleEntry({ item }: { item: ScheduleItem }) {
  const { t } = useTranslation();
  const label = useLocalized();
  const [, month, day] = item.date.split('-');
  const isHospital = item.kind === 'hospital';

  return (
    <li className={`mp-entry kind-${item.kind}`}>
      <span className="mp-entry-dot" aria-hidden="true" />
      <time className="mp-entry-time" dateTime={`${item.date}T${item.time}+09:00`}>
        {month}.{day} {item.time}
      </time>
      <div className="mp-entry-body">
        <p className="mp-entry-title">
          {label(item.title)}
          <span className={`mp-tag ${isHospital ? 'tag-blue' : 'tag-green'}`}>{t(TAG_KEY[item.kind])}</span>
        </p>
        <p className="mp-entry-place">
          {item.place.map((x) => label(x)).join(' · ')}
          {item.mapQuery && (
            <>
              {' · '}
              <a
                href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(item.mapQuery)}`}
                target="_blank"
                rel="noreferrer"
              >
                {t('mypage.schedule.directions')}
                <ArrowUpRightIcon />
              </a>
            </>
          )}
        </p>
      </div>
    </li>
  );
}
