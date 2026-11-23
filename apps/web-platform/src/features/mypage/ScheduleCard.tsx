import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { CalendarIcon, DaeguSkyline, PlusIcon } from './icons';
import { ScheduleEntry } from './ScheduleEntry';
import { KST, todayKst } from '../../lib/common';
import type { ScheduleItem } from './sampleData';
import { byDateTime, planToItem, useTripSchedule } from './tripSchedule';

interface Props {
  start: string;
  end: string;
  items: ScheduleItem[]; // 예시 일정 (데모 계정). 내가 넣은 일정은 이 카드가 tripSchedule에서 읽어 합침
}

const MAX_TEXT = 60;
// 시간은 목록에서 한 번 고르면 바로 닫히게 (브라우저 시간 입력창은 고른 뒤에도 열려 있음). 07:00~22:30, 30분 단위
const TIMES = Array.from({ length: 32 }, (_, i) => `${String(7 + Math.floor(i / 2)).padStart(2, '0')}:${i % 2 ? '30' : '00'}`);

// 여행 기간 표시: 언어별 날짜 형식 (예: 11월 20일 – 22일, Nov 20 – 22)
// formatRange는 ES2021 타입이라 tsconfig(ES2020)에 맞춰 타입만 보강
type RangeFormat = Intl.DateTimeFormat & { formatRange(a: Date, b: Date): string };

function formatRange(start: string, end: string, lang: string) {
  const fmt = new Intl.DateTimeFormat(lang, { month: 'long', day: 'numeric', timeZone: KST });
  return (fmt as RangeFormat).formatRange(new Date(`${start}T00:00:00+09:00`), new Date(`${end}T00:00:00+09:00`));
}

export function ScheduleCard({ start, end, items }: Props) {
  const { t, i18n } = useTranslation();
  const { plans, add, remove } = useTripSchedule();
  const [open, setOpen] = useState(false);
  const [date, setDate] = useState(todayKst());
  const [time, setTime] = useState('');
  const [text, setText] = useState('');

  const mine = new Set(plans.map((p) => p.id));
  const all = [...items, ...plans.map(planToItem)].sort(byDateTime);
  // 여행 기간: 데모 예시 기간이 없으면 내 일정의 첫날~마지막 날
  const from = start || all[0]?.date;
  const to = end || all[all.length - 1]?.date;

  const today = todayKst();
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!date || date < today || !text.trim()) return; // 지난 날짜는 등록 안 함
    add({ date, time, text: text.trim() });
    setText('');
    setTime('');
    setOpen(false);
  };

  return (
    <section className="mp-card mp-schedule" aria-labelledby="mp-schedule-title">
      <DaeguSkyline />
      <div className="mp-card-head">
        <h2 id="mp-schedule-title">{t('mypage.schedule.title')}</h2>
      </div>
      {from && to && (
        <p className="mp-trip-range">
          <CalendarIcon />
          {formatRange(from, to, i18n.language)}
        </p>
      )}
      {all.length > 0 && (
        // 일정이 많으면 이 안에서만 스크롤 (카드 높이는 그대로)
        <div className="mp-timeline-scroll">
          <ol className="mp-timeline">
            {all.map((item) => (
              <ScheduleEntry key={item.id} item={item} onRemove={mine.has(item.id) ? () => remove(item.id) : undefined} />
            ))}
          </ol>
        </div>
      )}

      {open ? (
        <form className="mp-plan-form" onSubmit={submit}>
          <label>
            <span>{t('mypage.schedule.form.date')}</span>
            <input type="date" value={date} min={today} required onChange={(e) => setDate(e.target.value)} />
          </label>
          <label>
            <span>{t('mypage.schedule.form.time')}</span>
            <select value={time} onChange={(e) => setTime(e.target.value)}>
              <option value="">{t('mypage.schedule.form.noTime')}</option>
              {TIMES.map((x) => (
                <option key={x} value={x}>
                  {x}
                </option>
              ))}
            </select>
          </label>
          <label className="mp-plan-text">
            <span>{t('mypage.schedule.form.text')}</span>
            <input
              type="text"
              value={text}
              required
              maxLength={MAX_TEXT}
              placeholder={t('mypage.schedule.form.placeholder')}
              onChange={(e) => setText(e.target.value)}
            />
          </label>
          <div className="mp-plan-actions">
            <button type="button" className="mp-plan-cancel" onClick={() => setOpen(false)}>
              {t('mypage.schedule.form.cancel')}
            </button>
            <button type="submit" className="mp-plan-save" disabled={!date || date < today || !text.trim()}>
              {t('mypage.schedule.form.save')}
            </button>
          </div>
        </form>
      ) : (
        <button type="button" className="mp-text-link mp-add" onClick={() => setOpen(true)}>
          <PlusIcon />
          {t('mypage.schedule.add')}
        </button>
      )}
    </section>
  );
}
