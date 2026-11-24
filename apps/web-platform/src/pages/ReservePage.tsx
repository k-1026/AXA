import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { todayKst } from '../lib/common';
import { nowKstTime } from '../features/consult/format';
import { useConsultThreads } from '../features/consult/useConsultThreads';
import { BookingConsentFields, consentReady, emptyConsent, toExtra, useResidencyCheck } from '../features/consult/BookingConsentFields';
import { useAuth } from '../components/auth';
import { bookingErrorKey } from '../features/consult/bookingErrors';
import { useHospitals } from '../features/hospital/useHospitals';
import { hospitalNames, useHospitalName } from '../features/hospital/name';
import { addDays, DAYS_AHEAD, isBookable, slotsFor } from '../features/reserve/availability';

// 공개 URL로 배포된 화면인지 (localhost·127.0.0.1이 아니면 공개 배포로 봄) — "예시 일정 · 실제 예약 아님" 문구용
const IS_PUBLIC_DEPLOY = typeof window !== 'undefined'
  && !['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname);

// 병원 목록의 "예약하기": 달력에서 날짜 → 그날 예약 가능한 시간 → 예약 신청
// 신청하면 그 병원 상담에 예약 요청(확인 대기)으로 남고, 확정은 병원이 한다
export function ReservePage() {
  const { t, i18n } = useTranslation();
  const { id } = useParams();
  const state = useHospitals();
  const nameOf = useHospitalName();
  const consult = useConsultThreads();
  const today = todayKst();
  const nowTime = nowKstTime();
  const [month, setMonth] = useState(today.slice(0, 7)); // YYYY-MM
  const [date, setDate] = useState('');
  const [time, setTime] = useState('');
  const [done, setDone] = useState(false);
  const [consent, setConsent] = useState(emptyConsent);
  const residency = useAuth().user?.residency;
  const checkResidency = useResidencyCheck();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const locale = i18n.language;
  const lastDay = addDays(today, DAYS_AHEAD - 1);
  const h = state.status === 'ready' ? state.data.items.find((x) => x.id === id) : undefined;

  // 달력 칸: 월요일 시작, 앞쪽 빈칸 포함
  const cells = useMemo(() => {
    const first = `${month}-01`;
    const lead = (new Date(`${first}T00:00:00Z`).getUTCDay() + 6) % 7;
    const days = new Date(Date.UTC(Number(month.slice(0, 4)), Number(month.slice(5, 7)), 0)).getUTCDate();
    return [...Array(lead).fill(''), ...Array.from({ length: days }, (_, i) => addDays(first, i))] as string[];
  }, [month]);

  if (state.status === 'loading') return <p className="list-status">{t('map.loading')}</p>;
  if (state.status === 'error') return <p className="list-status">{t('map.error')}</p>;
  if (!h) {
    return (
      <section className="placeholder-page">
        <p>{t('hospital.notFound')}</p>
        <Link to="/hospitals">← {t('reserve.back')}</Link>
      </section>
    );
  }

  const slots = date ? slotsFor(h, date, today, nowTime) : [];
  const weekdays = Array.from({ length: 7 }, (_, i) =>
    new Intl.DateTimeFormat(locale, { weekday: 'short', timeZone: 'UTC' }).format(new Date(Date.UTC(2024, 0, 1 + i))),
  );
  const monthTitle = new Intl.DateTimeFormat(locale, { year: 'numeric', month: 'long', timeZone: 'UTC' }).format(new Date(`${month}-01T00:00:00Z`));
  const dateLabel = (d: string) =>
    new Intl.DateTimeFormat(locale, { month: 'long', day: 'numeric', weekday: 'short', timeZone: 'UTC' }).format(new Date(`${d}T00:00:00Z`));
  const shiftMonth = (n: number) => {
    const d = new Date(`${month}-01T00:00:00Z`);
    d.setUTCMonth(d.getUTCMonth() + n);
    setMonth(d.toISOString().slice(0, 7));
  };

  const pickDate = (d: string) => {
    setDate(d);
    setTime('');
  };

  const member = consult.mode === 'member';
  const submit = async () => {
    if (!date || !time) return;
    if (member && residency === 'resident') return setError(t('residency.err.notEligible'));
    if (member && !consentReady(consent, false, residency)) return setError(t('booking.err.consentNeeded'));
    setError('');
    setBusy(true);
    try {
      if (member) await checkResidency(consent);
      await consult.requestBookingFor(
        { hospitalId: h.id, name: hospitalNames(h), dept: h.depts[0], district: h.district, photo: h.photo },
        { date, time, language: locale },
        member ? toExtra(consent, false) : undefined,
      );
      setDone(true);
    } catch (err) {
      setError(t(bookingErrorKey(err)));
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    return (
      <section className="reserve-page">
        <div className="reserve-done">
          <span className="reserve-done-mark" aria-hidden>✓</span>
          <h1>{t('reserve.doneTitle')}</h1>
          <p className="reserve-done-name">{nameOf(h)}</p>
          <p className="reserve-done-when">{dateLabel(date)} {time}</p>
          <p className="reserve-note">{t('reserve.doneBody')}</p>
          <div className="reserve-done-actions">
            <Link to="/mypage/bookings" className="is-primary">{t('reserve.toBookings')}</Link>
            <Link to={`/booking?hospital=${encodeURIComponent(h.id)}`}>{t('reserve.toConsult')}</Link>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="reserve-page">
      <Link to="/hospitals" className="back-link">← {t('reserve.back')}</Link>
      <header className="reserve-head">
        <p className="hospital-type">{t('reserve.title')}</p>
        <h1>{nameOf(h)}</h1>
      </header>
      {IS_PUBLIC_DEPLOY && (
        // 공개 배포(Vercel 등)에서만: 예시 예약 시간이 실제 예약처럼 보이지 않게 (로컬 시연은 표시 안 함)
        <p className="reserve-example-notice" role="note">{t('reserve.exampleNotice')}</p>
      )}
      {member && residency === 'resident' && (
        // 국내 거주로 답한 계정은 날짜를 고르기 전에 먼저 알림 (결정 28)
        <p className="residency-blocked" role="alert">
          {t('residency.bookingBlocked')} <Link to="/mypage">{t('residency.editLink')}</Link>
        </p>
      )}

      <div className="reserve-grid">
        <div className="reserve-card">
          <h2>{t('reserve.pickDate')}</h2>
          <div className="reserve-month">
            <button type="button" onClick={() => shiftMonth(-1)} disabled={month <= today.slice(0, 7)} aria-label={t('reserve.prevMonth')}>‹</button>
            <strong>{monthTitle}</strong>
            <button type="button" onClick={() => shiftMonth(1)} disabled={month >= lastDay.slice(0, 7)} aria-label={t('reserve.nextMonth')}>›</button>
          </div>
          <div className="reserve-cal" role="grid">
            {weekdays.map((w) => <span key={w} className="reserve-wd">{w}</span>)}
            {cells.map((d, i) => {
              if (!d) return <span key={`e${i}`} />;
              const ok = isBookable(h, d, today, nowTime);
              const cls = ['reserve-day', ok && 'is-open', d === date && 'is-selected', d === today && 'is-today'].filter(Boolean).join(' ');
              return (
                <button key={d} type="button" className={cls} disabled={!ok} aria-pressed={d === date} onClick={() => pickDate(d)}>
                  {Number(d.slice(8))}
                </button>
              );
            })}
          </div>
          <p className="reserve-legend">
            <span className="dot is-open" /> {t('reserve.available')}
            <span className="dot" /> {t('reserve.unavailable')}
          </p>
        </div>

        <div className="reserve-card">
          <h2>{t('reserve.pickTime')}</h2>
          {!date ? (
            <p className="reserve-empty">{t('reserve.dateFirst')}</p>
          ) : (
            <>
              <p className="reserve-selected">{dateLabel(date)}</p>
              <div className="reserve-times">
                {slots.map((s) => (
                  <button key={s.time} type="button" className={s.time === time ? 'reserve-time is-selected' : 'reserve-time'}
                    disabled={!s.free} aria-pressed={s.time === time} onClick={() => setTime(s.time)}>
                    {s.time}
                  </button>
                ))}
              </div>
            </>
          )}
          {date && time && (
            <div className="reserve-confirm">
              <p><strong>{dateLabel(date)} {time}</strong></p>
              {member && <BookingConsentFields value={consent} onChange={setConsent} hasNote={false} />}
              {error && <p className="consult-form-error" role="alert">{error}</p>}
              <button type="button" className="reserve-submit" onClick={submit} disabled={busy}>
                {busy ? t('auth.submitting') : t('reserve.submit')}
              </button>
            </div>
          )}
          <p className="reserve-note">{t('reserve.note')}</p>
        </div>
      </div>
    </section>
  );
}
