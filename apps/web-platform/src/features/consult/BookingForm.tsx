import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { LANGUAGES } from '../../i18n';
import { todayKst } from '../../lib/common';
import { nowKstTime } from './format';
import type { BookingRequest } from './types';

// 상담 가능 시간 안에서 30분 단위
const TIMES = Array.from({ length: 18 }, (_, i) => `${String(9 + Math.floor(i / 2)).padStart(2, '0')}:${i % 2 ? '30' : '00'}`);

interface Props {
  initial?: BookingRequest; // 예약 변경일 때 기존 값
  onSubmit: (b: Omit<BookingRequest, 'status'>) => void;
  onCancel: () => void;
}

// 예약 신청서. 보내면 병원에 "확인 대기"로 전달되고, 확정은 병원이 한다
export function BookingForm({ initial, onSubmit, onCancel }: Props) {
  const { t, i18n } = useTranslation();
  const [date, setDate] = useState(initial?.date ?? '');
  const [time, setTime] = useState(initial?.time ?? '14:00');
  const [language, setLanguage] = useState<string>(initial?.language ?? i18n.language);
  const [note, setNote] = useState(initial?.note ?? '');
  const [error, setError] = useState('');

  // 오늘(한국 시간)을 고르면 이미 지난 시간은 고를 수 없다
  const timesFor = (d: string) => (d === todayKst() ? TIMES.filter((x) => x > nowKstTime()) : TIMES);
  const times = timesFor(date);

  const changeDate = (d: string) => {
    setDate(d);
    setError('');
    const ok = timesFor(d);
    if (ok.length && !ok.includes(time)) setTime(ok[0]); // 고른 시간이 지났으면 가장 가까운 시간으로
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!date || date < todayKst()) return setError(t('consult.form.errDate'));
    if (!timesFor(date).includes(time)) return setError(t('consult.form.errTime'));
    onSubmit({ date, time, language, note: note.trim() || undefined });
  };

  return (
    <form className="consult-form" onSubmit={submit} noValidate>
      <h3>{t(initial ? 'consult.form.changeTitle' : 'consult.form.title')}</h3>
      <div className="consult-form-row">
        <label>
          {t('consult.form.date')}
          <input type="date" value={date} min={todayKst()} onChange={(e) => changeDate(e.target.value)} />
        </label>
        <label>
          {t('consult.form.time')}
          <select value={time} onChange={(e) => setTime(e.target.value)}>
            {times.map((x) => (
              <option key={x} value={x}>{x}</option>
            ))}
          </select>
        </label>
        <label>
          {t('consult.form.language')}
          <select value={language} onChange={(e) => setLanguage(e.target.value)}>
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>{l.label}</option>
            ))}
          </select>
        </label>
      </div>
      <label>
        {t('consult.form.note')}
        <textarea rows={2} maxLength={300} value={note} placeholder={t('consult.form.notePlaceholder')} onChange={(e) => setNote(e.target.value)} />
      </label>
      {error && <p className="consult-form-error" role="alert">{error}</p>}
      <p className="consult-form-hint">{t(initial ? 'consult.form.changeHint' : 'consult.form.hint')}</p>
      <div className="consult-form-actions">
        <button type="button" onClick={onCancel}>{t('consult.form.cancel')}</button>
        <button type="submit" className="is-primary">{t(initial ? 'consult.form.changeSubmit' : 'consult.form.submit')}</button>
      </div>
    </form>
  );
}
