import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckIcon } from './icons';
import type { ChecklistItem } from './sampleData';

export function ChecklistCard({ initial }: { initial: ChecklistItem[] }) {
  const { t } = useTranslation();
  // 저장은 아직 없음 (로그인·백엔드 연결 후)
  const [items, setItems] = useState(initial);
  const done = items.filter((i) => i.done).length;

  const toggle = (key: string) =>
    setItems((prev) => prev.map((i) => (i.key === key ? { ...i, done: !i.done } : i)));

  return (
    <section className="mp-card mp-checklist" aria-labelledby="mp-checklist-title">
      <div className="mp-card-head">
        <h2 id="mp-checklist-title">{t('mypage.checklist.title')}</h2>
        <span className="mp-progress-text">
          {t('mypage.checklist.progress', { total: items.length, done })}
        </span>
      </div>
      <div
        className="mp-progress"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={items.length}
        aria-valuenow={done}
        aria-labelledby="mp-checklist-title"
      >
        <span style={{ width: `${(done / items.length) * 100}%` }} />
      </div>
      <ul className="mp-check-list">
        {items.map((item) => (
          <li key={item.key}>
            <label className="mp-check">
              <input type="checkbox" checked={item.done} onChange={() => toggle(item.key)} />
              <span className="mp-check-box" aria-hidden="true">
                <CheckIcon />
              </span>
              {t(`mypage.checklist.items.${item.key}`)}
            </label>
          </li>
        ))}
      </ul>
    </section>
  );
}
