import { useTranslation } from 'react-i18next';
import { ArrowUpRightIcon } from './icons';
import { useLocalized } from '../../lib/common';
import type { ScheduleItem } from './sampleData';

// 예시 일정의 종류 표시. 내가 넣은 일정(plan)은 삭제 버튼이 있어 표시 없음
const TAG_KEY: Partial<Record<ScheduleItem['kind'], string>> = {
  hospital: 'mypage.schedule.tag.userAdded',
  experience: 'mypage.schedule.tag.experience',
  tour: 'mypage.schedule.tag.tour',
};

export function ScheduleEntry({ item, onRemove }: { item: ScheduleItem; onRemove?: () => void }) {
  const { t } = useTranslation();
  const label = useLocalized();
  const [, month, day] = item.date.split('-');
  const tag = TAG_KEY[item.kind];

  return (
    <li className={`mp-entry kind-${item.kind}`}>
      <span className="mp-entry-dot" aria-hidden="true" />
      <time className="mp-entry-time" dateTime={item.time ? `${item.date}T${item.time}+09:00` : item.date}>
        {month}.{day} {item.time}
      </time>
      <div className="mp-entry-body">
        <p className="mp-entry-title">
          {label(item.title)}
          {tag && <span className={`mp-tag ${item.kind === 'hospital' ? 'tag-blue' : 'tag-green'}`}>{t(tag)}</span>}
          {onRemove && (
            <button type="button" className="mp-entry-remove" onClick={onRemove}>
              {t('mypage.schedule.remove')}
            </button>
          )}
        </p>
        {(item.place.length > 0 || item.mapQuery) && (
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
        )}
      </div>
    </li>
  );
}
