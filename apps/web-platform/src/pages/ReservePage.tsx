import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LANGUAGES } from '../i18n';
import { todayKst } from '../lib/common';
import { nowKstTime } from '../features/consult/format';
import { useConsultThreads } from '../features/consult/useConsultThreads';
import { BookingConsentFields, consentReady, emptyConsent, toExtra, useResidencyCheck, type ConsentState } from '../features/consult/BookingConsentFields';
import { readSessionSetting, writeSessionSetting } from '../components/storage';
import { useAuth } from '../components/auth';
import { bookingErrorKey } from '../features/consult/bookingErrors';
import { useHospitals } from '../features/hospital/useHospitals';
import { hospitalNames, useHospitalName } from '../features/hospital/name';
import { addDays, DAYS_AHEAD, isBookable, slotsFor } from '../features/reserve/availability';
import type { DepartmentKey } from '../features/hospital/types';

// 공개 URL로 배포된 화면인지 (localhost·127.0.0.1이 아니면 공개 배포로 봄) — "예시 일정 · 실제 예약 아님" 문구용
const IS_PUBLIC_DEPLOY = typeof window !== 'undefined'
  && !['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname);

// 다른 화면에 갔다 와도 고른 값 유지 (11/27): 병원별로 이 탭(sessionStorage)에만. 예약을 보내면 지움
// 지난 날짜·이미 지난 시간·예약 안 되는 시간은 다시 채우지 않음 (아래 useEffect)
type Draft = { month: string; date: string; time: string; dept: DepartmentKey | ''; language: string; consent: ConsentState };
const draftKey = (id?: string) => `reserveDraft.${id ?? ''}`;
function readDraft(id: string | undefined, today: string): Partial<Draft> {
  try {
    const d = JSON.parse(readSessionSetting(draftKey(id)) ?? 'null') as Partial<Draft> | null;
    if (!d) return {};
    if (d.date && d.date < today) return { ...d, month: undefined, date: '', time: '' };
    return d;
  } catch {
    return {};
  }
}

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
  const [draft] = useState(() => readDraft(id, today));
  const [month, setMonth] = useState(draft.month ?? today.slice(0, 7)); // YYYY-MM
  const [date, setDate] = useState(draft.date ?? '');
  const [time, setTime] = useState(draft.time ?? '');
  // 진료과·상담 언어는 환자가 직접 고름 (전에는 병원 첫 진료과·화면 언어로 그냥 보냄 → 한국어 화면이면 상담 언어 ko, 11/26)
  const [dept, setDept] = useState<DepartmentKey | ''>(draft.dept ?? '');
  const [language, setLanguage] = useState(draft.language ?? '');
  const [done, setDone] = useState(false);
  const [consent, setConsent] = useState<ConsentState>(() => ({ ...emptyConsent(), ...draft.consent }));
  const residency = useAuth().user?.residency;
  const checkResidency = useResidencyCheck();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const locale = i18n.language;
  const lastDay = addDays(today, DAYS_AHEAD - 1);
  const h = state.status === 'ready' ? state.data.items.find((x) => x.id === id) : undefined;

  // 다시 채운 날짜·시간이 지금은 예약 안 되면 비움 (병원 정보를 받은 뒤 한 번)
  useEffect(() => {
    if (!h || !date) return;
    if (!isBookable(h, date, today, nowTime)) { setDate(''); setTime(''); return; }
    if (time && !slotsFor(h, date, today, nowTime).some((s) => s.time === time && s.free)) setTime('');
  }, [h]); // 병원 정보가 처음 들어올 때만 (고르는 중에는 화면이 이미 막음)

  useEffect(() => {
    if (done) return;
    writeSessionSetting(draftKey(id), JSON.stringify({ month, date, time, dept, language, consent } satisfies Draft));
  }, [id, done, month, date, time, dept, language, consent]);

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
  if (!h.demo) {
    return (
      <section className="placeholder-page">
        <p>{t('hospital.notJoined')}</p>
        {h.tel && <p><a href={`tel:${h.tel}`}>{t('hospital.callBtn')} · {h.tel}</a></p>}
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
  const deptValue = dept || (h.depts.length === 1 ? h.depts[0] : ''); // 진료과가 하나뿐이면 그것
  // 예약 버튼: 진료과·상담 언어를 고르고, 회원이면 국적·단기 방문·전달 동의까지 해야 눌림
  const canSubmit = !!date && !!time && !!deptValue && !!language
    && (!member || (residency !== 'resident' && consentReady(consent, false, residency)));
  const submit = async () => {
    if (!canSubmit) return;
    if (member && residency === 'resident') return setError(t('residency.err.notEligible'));
    if (member && !consentReady(consent, false, residency)) return setError(t('booking.err.consentNeeded'));
    setError('');
    setBusy(true);
    try {
      if (member) await checkResidency(consent);
      await consult.requestBookingFor(
        { hospitalId: h.id, name: hospitalNames(h), dept: deptValue, district: h.district, photo: h.photo },
        { date, time, language },
        member ? toExtra(consent, false) : undefined,
      );
      writeSessionSetting(draftKey(id), null);
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
              <div className="reserve-fields">
                <label className="auth-field">
                  <span>{t('reserve.dept')}</span>
                  <select value={deptValue} onChange={(e) => setDept(e.target.value as DepartmentKey)}>
                    <option value="" disabled>{t('booking.choose')}</option>
                    {h.depts.map((d) => <option key={d} value={d}>{t(`dept.${d}`)}</option>)}
                  </select>
                </label>
                <label className="auth-field">
                  <span>{t('reserve.language')}</span>
                  <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                    <option value="" disabled>{t('booking.choose')}</option>
                    {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
                  </select>
                </label>
              </div>
              {member && <BookingConsentFields value={consent} onChange={setConsent} hasNote={false} />}
              {error && <p className="consult-form-error" role="alert">{error}</p>}
              <button type="button" className="reserve-submit" onClick={submit} disabled={busy || !canSubmit}>
                {busy ? t('auth.submitting') : t('reserve.submit')}
              </button>
              {!canSubmit && !busy && residency !== 'resident' && <p className="reserve-need">{t('reserve.needAll')}</p>}
            </div>
          )}
          <p className="reserve-note">{t('reserve.note')}</p>
        </div>
      </div>
    </section>
  );
}
