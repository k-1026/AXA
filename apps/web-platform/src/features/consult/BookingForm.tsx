import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { LANGUAGES } from '../../i18n';
import { todayKst } from '../../lib/common';
import type { BookingExtra } from './bookingApi';
import { useAuth } from '../../components/auth';
import { BookingConsentFields, consentReady, emptyConsent, toExtra, useResidencyCheck } from './BookingConsentFields';
import { bookingErrorKey } from './bookingErrors';
import { nowKstTime } from './format';
import type { BookingRequest } from './types';
import type { Hospital } from '../hospital/types';
import { openTimes } from '../reserve/availability';

// 병원 정보를 못 찾았을 때만 쓰는 기본 시간 (30분 단위). 병원을 알면 그 병원 진료시간 안만 (휴진일은 없음)
const TIMES = Array.from({ length: 18 }, (_, i) => `${String(9 + Math.floor(i / 2)).padStart(2, '0')}:${i % 2 ? '30' : '00'}`);

interface Props {
  initial?: BookingRequest; // 예약 변경일 때 기존 값
  hospital?: Hospital; // 진료시간 (없으면 기본 시간)
  // member = 실제 회원 → 국적·단기 방문·동의를 같이 받아 서버에 보냄. 실패하면 Promise가 거부되고 폼에 오류를 보여 준다
  member?: boolean;
  onSubmit: (b: Omit<BookingRequest, 'status'>, extra?: BookingExtra) => void | Promise<void>;
  onCancel: () => void;
}

// 예약 신청서. 보내면 병원에 "확인 대기"로 전달되고, 확정은 병원이 한다
export function BookingForm({ initial, hospital, member = false, onSubmit, onCancel }: Props) {
  const { t, i18n } = useTranslation();
  const [date, setDate] = useState(initial?.date ?? '');
  const [time, setTime] = useState(initial?.time ?? '14:00');
  const [language, setLanguage] = useState<string>(initial?.language ?? i18n.language);
  const [note, setNote] = useState(initial?.note ?? '');
  const [consent, setConsent] = useState(emptyConsent);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const hasNote = !!note.trim();
  const residency = useAuth().user?.residency;
  const checkResidency = useResidencyCheck();

  // 오늘(한국 시간)을 고르면 이미 지난 시간은 고를 수 없다
  const timesFor = (d: string) => {
    const base = hospital ? (d ? openTimes(hospital, d) : []) : TIMES;
    return d === todayKst() ? base.filter((x) => x > nowKstTime()) : base;
  };
  const times = timesFor(date);
  const closedDay = !!hospital && !!date && openTimes(hospital, date).length === 0;

  const changeDate = (d: string) => {
    setDate(d);
    setError('');
    const ok = timesFor(d);
    if (ok.length && !ok.includes(time)) setTime(ok[0]); // 고른 시간이 지났으면 가장 가까운 시간으로
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!date || date < todayKst()) return setError(t('consult.form.errDate'));
    if (closedDay) return setError(t('consult.form.errClosed'));
    if (!timesFor(date).includes(time)) return setError(t('consult.form.errTime'));
    if (member && residency === 'resident') return setError(t('residency.err.notEligible'));
    if (member && !consentReady(consent, hasNote, residency)) return setError(t('booking.err.consentNeeded'));
    setError('');
    setBusy(true);
    try {
      if (member) await checkResidency(consent);
      await onSubmit({ date, time, language, note: note.trim() || undefined }, member ? toExtra(consent, hasNote) : undefined);
    } catch (err) {
      setError(t(bookingErrorKey(err)));
    } finally {
      setBusy(false);
    }
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
          <select value={times.includes(time) ? time : ''} onChange={(e) => setTime(e.target.value)} disabled={!times.length}>
            {!times.length && <option value="">{closedDay ? t('consult.form.closedOption') : '—'}</option>}
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
      {member && <BookingConsentFields value={consent} onChange={setConsent} hasNote={hasNote} />}
      {closedDay && !error && <p className="consult-form-error" role="status">{t('consult.form.errClosed')}</p>}
      {error && <p className="consult-form-error" role="alert">{error}</p>}
      <p className="consult-form-hint">{t(initial ? 'consult.form.changeHint' : 'consult.form.hint')}</p>
      <div className="consult-form-actions">
        <button type="button" onClick={onCancel}>{t('consult.form.cancel')}</button>
        {/* 회원은 국적·단기 방문·필수 동의를 다 해야 눌림 (예약 화면과 같게, 11/26) */}
        <button type="submit" className="is-primary" disabled={busy || (member && !consentReady(consent, hasNote, residency))}>
          {busy ? t('auth.submitting') : t(initial ? 'consult.form.changeSubmit' : 'consult.form.submit')}
        </button>
      </div>
    </form>
  );
}
