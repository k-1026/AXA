import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { LANGUAGES } from '../../i18n';
import { CalendarIcon, ChevronRightIcon, GlobeIcon, InfoIcon } from '../mypage/icons';
import { bookingDateTime } from './format';
import { displayStatus, type BookingRequest, type DisplayStatus } from './types';

// 카드 아래 안내 문구
const NOTE: Partial<Record<DisplayStatus, string>> = {
  pending: 'consult.pendingNote',
  proposed: 'bookings.proposedNote',
  rejected: 'bookings.rejectedNote',
  expired: 'bookings.expiredNote',
  visited: 'consult.visitedNote',
};

// 대화 속 예약 신청 카드. 병원이 확인하기 전까지는 "확인 대기"
export function BookingCard({ booking, sentAt }: { booking: BookingRequest; sentAt: string }) {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const langLabel = LANGUAGES.find((l) => l.code === booking.language)?.label ?? booking.language;
  const status = displayStatus(booking);

  return (
    <article className="consult-booking">
      <header>
        <span className="consult-booking-icon">
          <CalendarIcon />
        </span>
        <h3>{t('consult.bookingTitle')}</h3>
        <span className={`consult-status is-${status}`}>{t(`consult.status.${status}`)}</span>
      </header>
      <p className="consult-booking-line">
        <CalendarIcon />
        {bookingDateTime(booking.date, booking.time, i18n.language)}
      </p>
      <p className="consult-booking-line">
        <GlobeIcon />
        {t('consult.bookingLanguage', { lang: langLabel })}
      </p>
      {open && (
        <dl className="consult-booking-detail">
          <dt>{t('consult.sentAt')}</dt>
          <dd>{new Date(sentAt).toLocaleString(i18n.language, { timeZone: 'Asia/Seoul' })}</dd>
          <dt>{t('consult.note')}</dt>
          <dd>{booking.note || '—'}</dd>
        </dl>
      )}
      <footer>
        <span>
          <InfoIcon />
          {t(NOTE[status] ?? 'consult.decidedNote')}
        </span>
        <button type="button" aria-expanded={open} onClick={() => setOpen(!open)}>
          {t(open ? 'consult.hideDetail' : 'consult.showDetail')}
          <ChevronRightIcon />
        </button>
      </footer>
    </article>
  );
}
