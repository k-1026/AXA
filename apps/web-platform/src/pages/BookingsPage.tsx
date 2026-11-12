import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LANGUAGES } from '../i18n';
import { KST, useLocalized } from '../lib/common';
import { ArrowLeftIcon, CalendarIcon, InfoIcon, PencilIcon, PinIcon } from '../features/mypage/icons';
import { BookingForm } from '../features/consult/BookingForm';
import { HospitalThumb } from '../features/consult/HospitalThumb';
import { bookingDateFull } from '../features/consult/format';
import { useConsultThreads } from '../features/consult/useConsultThreads';
import { displayStatus, type BookingRequest, type DisplayStatus } from '../features/consult/types';
import { LegalLinks } from '../features/legal/LegalLinks';

type Filter = 'all' | 'pending' | 'confirmed' | 'visited' | 'cancelled';
type Sort = 'visit' | 'recent';
const FILTERS: Filter[] = ['all', 'pending', 'confirmed', 'visited', 'cancelled'];

// 상태 → 필터 묶음: 병원의 다른 시간 제안은 "확인 대기", 병원 거절·기간 만료는 "취소" 묶음에 함께
const GROUP: Record<DisplayStatus, Filter> = {
  pending: 'pending',
  proposed: 'pending',
  confirmed: 'confirmed',
  visited: 'visited',
  cancelled: 'cancelled',
  rejected: 'cancelled',
  expired: 'cancelled',
};
const group = (b: { booking: BookingRequest }) => GROUP[displayStatus(b.booking)];

// 상담에서 신청한 예약 모아 보기. 변경·취소는 환자가 하고, 확정·방문 완료 표시는 병원이 한다
export function BookingsPage() {
  const { t, i18n } = useTranslation();
  const text = useLocalized();
  const navigate = useNavigate();
  const consult = useConsultThreads();
  const [filter, setFilter] = useState<Filter>('all');
  const [sort, setSort] = useState<Sort>('visit');
  const [editing, setEditing] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState<string | null>(null);

  const all = consult.bookings;
  const count = (f: Filter) => (f === 'all' ? all.length : all.filter((b) => group(b) === f).length);
  const items = useMemo(
    () =>
      all
        .filter((b) => filter === 'all' || group(b) === filter)
        .sort((a, b) =>
          sort === 'visit'
            ? `${a.booking.date}T${a.booking.time}`.localeCompare(`${b.booking.date}T${b.booking.time}`)
            : Date.parse(b.message.at) - Date.parse(a.message.at),
        ),
    [all, filter, sort],
  );
  const langLabel = (code: string) => LANGUAGES.find((l) => l.code === code)?.label ?? code;
  const openChat = (id: string) => navigate(`/booking?hospital=${encodeURIComponent(id)}`);

  return (
    <div className="mypage">
      <nav className="mp-breadcrumb" aria-label="breadcrumb">
        <Link to="/mypage">{t('nav.mypage')}</Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page" className="is-current">
          {t('consult.manageBookings')}
        </span>
      </nav>

      <div className="mp-saved-top">
        <div>
          <Link to="/booking" className="mp-back">
            <ArrowLeftIcon />
            {t('bookings.backToChats')}
          </Link>
          <h1 className="mp-saved-title">{t('consult.manageBookings')}</h1>
          <p className="mp-greeting-sub">{t('bookings.subtitle')}</p>
        </div>
        <Link to="/booking" className="bk-top-link">
          <CalendarIcon />
          {t('bookings.toConsult')}
        </Link>
      </div>

      <div className="mp-saved-filter-row bk-filter-row">
        <div className="mp-pills" role="group" aria-label={t('bookings.filterLabel')}>
          {FILTERS.map((f) => (
            <button key={f} type="button" aria-pressed={filter === f} onClick={() => setFilter(f)}>
              {t(`bookings.filter.${f}`)} {count(f)}
            </button>
          ))}
        </div>
        <select className="mp-sort bk-sort" value={sort} onChange={(e) => setSort(e.target.value as Sort)} aria-label={t('bookings.sortLabel')}>
          <option value="visit">{t('bookings.sortVisit')}</option>
          <option value="recent">{t('bookings.sortRecent')}</option>
        </select>
      </div>

      <div className="bk-list">
        {items.length === 0 && <p className="mp-saved-empty">{t(all.length ? 'bookings.emptyFilter' : 'bookings.none')}</p>}
        {items.map(({ thread, message, booking }) => {
          const key = message.id;
          const status = displayStatus(booking);
          const cancelled = GROUP[status] === 'cancelled';
          const done = status === 'visited';
          // 변경·취소는 병원이 확정하기 전(대기·다른 시간 제안)에만 (계약 2절: 환자 취소는 pending·proposed에서만)
          const editable = status === 'pending' || status === 'proposed';
          return (
            <article key={key} className={`mp-card bk-card ${cancelled ? 'is-cancelled' : ''}`}>
              <HospitalThumb photo={thread.photo} size="lg" />
              <div className="bk-hospital">
                <h2>{text(thread.name)}</h2>
                <span className={`mp-tag dept-${thread.dept}`}>{t(`dept.${thread.dept}`)}</span>
                <span className="bk-place">
                  <PinIcon />
                  {t(`district.${thread.district}`)}
                </span>
              </div>
              <div className="bk-detail">
                <div className="bk-when">
                  <CalendarIcon />
                  <p>
                    {editable && <span className="bk-wish">{t('bookings.wish')} </span>}
                    {bookingDateFull(booking.date, booking.time, i18n.language)}
                  </p>
                  <span className={`consult-status is-${status}`}>{t(`consult.status.${status}`)}</span>
                </div>
                <p className="bk-sub">{t('bookings.kind', { lang: langLabel(booking.language) })}</p>
                <p className="bk-meta">
                  {(status === 'confirmed' || done) && booking.bookingNo && t('bookings.number', { no: booking.bookingNo })}
                  {done && booking.treatment && ` · ${text(booking.treatment)}`}
                  {status === 'pending' && (
                    <>
                      <InfoIcon />
                      {t('consult.pendingNote')}
                    </>
                  )}
                  {status === 'cancelled' &&
                    booking.cancelledAt &&
                    t('bookings.cancelledOn', { date: new Date(booking.cancelledAt).toLocaleDateString(i18n.language, { timeZone: KST }) })}
                  {status === 'rejected' && t('bookings.rejectedNote')}
                  {status === 'proposed' && t('bookings.proposedNote')}
                  {status === 'expired' && t('bookings.expiredNote')}
                </p>

                {editing === key ? (
                  <BookingForm
                    initial={booking}
                    onSubmit={(b) => {
                      consult.changeBooking(thread.hospitalId, message.id, b, t('bookings.changeMsg', { when: bookingDateFull(b.date, b.time, i18n.language) }));
                      setEditing(null);
                    }}
                    onCancel={() => setEditing(null)}
                  />
                ) : cancelling === key ? (
                  // 브라우저 확인창 대신 카드 안에서 한 번 더 확인
                  <div className="bk-confirm" role="group">
                    <p role="alert">{t('bookings.cancelConfirm')}</p>
                    <button type="button" onClick={() => setCancelling(null)}>
                      {t('bookings.keep')}
                    </button>
                    <button
                      type="button"
                      className="is-danger"
                      onClick={() => {
                        consult.cancelBooking(thread.hospitalId, message.id, t('bookings.cancelMsg', { when: bookingDateFull(booking.date, booking.time, i18n.language) }));
                        setCancelling(null);
                      }}
                    >
                      {t('bookings.cancel')}
                    </button>
                  </div>
                ) : (
                  <div className="bk-actions">
                    {done && (
                      <button type="button" className="is-primary" onClick={() => navigate('/aftercare')}>
                        {t('aftercare.aftercareButton')}
                      </button>
                    )}
                    {editable && (
                      <>
                        <button type="button" className="is-primary" onClick={() => setEditing(key)}>
                          <PencilIcon />
                          {t('bookings.change')}
                        </button>
                        <button type="button" onClick={() => setCancelling(key)}>
                          {t('bookings.cancel')}
                        </button>
                      </>
                    )}
                    <button type="button" onClick={() => openChat(thread.hospitalId)}>
                      {t('bookings.chat')}
                    </button>
                  </div>
                )}
              </div>
            </article>
          );
        })}
      </div>

      <p className="mp-saved-footnote bk-footnote">
        <InfoIcon />
        {t('bookings.footnote')}
        {consult.mode === 'demo' && ` · ${t('bookings.sampleNote')}`}
      </p>

      <LegalLinks />
    </div>
  );
}
