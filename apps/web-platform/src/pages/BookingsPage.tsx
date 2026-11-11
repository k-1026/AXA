import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LANGUAGES } from '../i18n';
import { useChatText } from '../features/chatbot/ChatMessages';
import { ArrowLeftIcon, CalendarIcon, InfoIcon, PencilIcon, PinIcon } from '../features/mypage/icons';
import { BookingForm } from '../features/consult/BookingForm';
import { HospitalThumb } from '../features/consult/HospitalThumb';
import { bookingDateFull } from '../features/consult/format';
import { useConsultThreads } from '../features/consult/useConsultThreads';
import type { BookingStatus } from '../features/consult/types';
import { LegalLinks } from '../features/legal/LegalLinks';

type Filter = 'all' | 'pending' | 'confirmed' | 'completed' | 'cancelled';
type Sort = 'visit' | 'recent';
const FILTERS: Filter[] = ['all', 'pending', 'confirmed', 'completed', 'cancelled'];

// 상담에서 신청한 예약 모아 보기. 변경·취소는 환자가 하고, 확정·방문 완료 표시는 병원이 한다
export function BookingsPage() {
  const { t, i18n } = useTranslation();
  const text = useChatText();
  const navigate = useNavigate();
  const consult = useConsultThreads();
  const [filter, setFilter] = useState<Filter>('all');
  const [sort, setSort] = useState<Sort>('visit');
  const [editing, setEditing] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState<string | null>(null);

  // 병원이 거절한 예약은 "취소" 묶음에 함께 보여준다
  const group = (s: BookingStatus): Filter => (s === 'declined' ? 'cancelled' : s);
  const all = consult.bookings;
  const count = (f: Filter) => (f === 'all' ? all.length : all.filter((b) => group(b.booking.status) === f).length);
  const items = useMemo(
    () =>
      all
        .filter((b) => filter === 'all' || group(b.booking.status) === filter)
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
          const cancelled = booking.status === 'cancelled' || booking.status === 'declined';
          const done = booking.status === 'completed';
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
                    {booking.status === 'pending' && <span className="bk-wish">{t('bookings.wish')} </span>}
                    {bookingDateFull(booking.date, booking.time, i18n.language)}
                  </p>
                  <span className={`consult-status is-${booking.status}`}>{t(`consult.status.${booking.status}`)}</span>
                </div>
                <p className="bk-sub">{t('bookings.kind', { lang: langLabel(booking.language) })}</p>
                <p className="bk-meta">
                  {(booking.status === 'confirmed' || done) && booking.bookingNo && t('bookings.number', { no: booking.bookingNo })}
                  {done && booking.treatment && ` · ${text(booking.treatment)}`}
                  {booking.status === 'pending' && (
                    <>
                      <InfoIcon />
                      {t('consult.pendingNote')}
                    </>
                  )}
                  {booking.status === 'cancelled' &&
                    booking.cancelledAt &&
                    t('bookings.cancelledOn', { date: new Date(booking.cancelledAt).toLocaleDateString(i18n.language, { timeZone: 'Asia/Seoul' }) })}
                  {booking.status === 'declined' && t('bookings.declinedNote')}
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
                    {!cancelled && !done && (
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
