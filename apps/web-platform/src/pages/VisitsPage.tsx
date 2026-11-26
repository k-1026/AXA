import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LegalLinks } from '../features/legal/LegalLinks';
import { useHospitals } from '../features/hospital/useHospitals';
import { HospitalThumb } from '../features/consult/HospitalThumb';
import { bookingDateFull } from '../features/consult/format';
import { VisitForm } from '../features/mypage/VisitForm';
import { ArrowLeftIcon, CalendarIcon, LockIcon } from '../features/mypage/icons';
import { useVisitLog } from '../features/mypage/visitLog';
import { useVisitedBookings } from '../features/mypage/visitedBookings';
import { useLocalized } from '../lib/common';

// 마이페이지 > 방문 기록. 본인만 쓰고 보는 다이어리 (공개 후기 아님, 병원 화면에 표시하지 않음)
// 방문한 병원·날짜·진료는 예약에서 자동 (병원이 "방문 완료" 표시한 건), "나의 경험"만 환자가 쓴다 (2026-11-26)
export function VisitsPage() {
  const { t, i18n } = useTranslation();
  const text = useLocalized();
  const state = useHospitals();
  const visited = useVisitedBookings();
  const { noteFor, saveNote, removeNote } = useVisitLog();
  const [editing, setEditing] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const hospitals = state.status === 'ready' ? state.data.items : [];

  return (
    <div className="mypage">
      <nav className="mp-breadcrumb" aria-label="breadcrumb">
        <Link to="/">{t('mypage.home')}</Link>
        <span aria-hidden="true">/</span>
        <Link to="/mypage">{t('nav.mypage')}</Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page" className="is-current">
          {t('mypage.visits.title')}
        </span>
      </nav>

      <div className="mp-saved-top">
        <div>
          <Link to="/mypage" className="mp-back">
            <ArrowLeftIcon />
            {t('nav.mypage')}
          </Link>
          <h1 className="mp-saved-title">
            {t('mypage.visits.title')} <span>{visited.length}</span>
          </h1>
          <p className="mp-greeting-sub">{t('mypage.visits.subtitle')}</p>
        </div>
        <span className="visit-private">
          <LockIcon />
          {t('mypage.visits.private')}
        </span>
      </div>

      <section className="mp-saved-list">
        {visited.length === 0 && <p className="mp-saved-empty">{t('mypage.visits.none')}</p>}
        {visited.map(({ thread, message, booking }) => {
          const key = message.id;
          const note = noteFor(key);
          const inData = hospitals.some((h) => h.id === thread.hospitalId);
          const name = text(thread.name);
          return (
            <article key={key} className="mp-card visit-card">
              {/* 자동으로 채워지는 부분: 병원·날짜·진료 (예약에서) */}
              <div className="visit-auto">
                <HospitalThumb photo={thread.photo} size="lg" />
                <div className="visit-auto-body">
                  <div className="visit-head">
                    <h3>
                      {inData ? <Link to={`/hospitals/${encodeURIComponent(thread.hospitalId)}`}>{name}</Link> : name}
                    </h3>
                    <span className="visit-auto-tag">{t('mypage.visits.auto')}</span>
                  </div>
                  <p className="visit-when">
                    <CalendarIcon />
                    <time dateTime={booking.date}>{bookingDateFull(booking.date, booking.time, i18n.language)}</time>
                  </p>
                  <p className="visit-meta">
                    <span className={`mp-tag dept-${thread.dept}`}>{t(`dept.${thread.dept}`)}</span>
                    {booking.treatment && (
                      <span>
                        {t('mypage.visits.treatment')}: {text(booking.treatment)}
                      </span>
                    )}
                  </p>
                </div>
              </div>

              {/* 환자가 쓰는 부분: 나의 경험 */}
              <div className="visit-mine">
                {editing === key || !note ? (
                  <VisitForm
                    key={`${key}-${editing === key}`}
                    initial={note || undefined}
                    onSubmit={(n) => {
                      saveNote({ bookingId: key, hospitalId: thread.hospitalId, hospitalName: name, date: booking.date, note: n });
                      setEditing(null);
                    }}
                    onCancel={note ? () => setEditing(null) : undefined}
                  />
                ) : (
                  <>
                    <h4 className="visit-mine-title">{t('mypage.visits.note')}</h4>
                    <p className="visit-note">{note}</p>
                    {/* 브라우저 확인창(window.confirm)은 앱 내 브라우저 등에서 막힐 수 있어 카드 안에서 확인 */}
                    {deleting === key ? (
                      <div className="visit-actions visit-delete-confirm" role="group">
                        <p role="alert">{t('mypage.visits.deleteConfirm')}</p>
                        <button type="button" className="visit-button" onClick={() => setDeleting(null)}>
                          {t('mypage.visits.cancel')}
                        </button>
                        <button
                          type="button"
                          className="visit-button is-danger"
                          onClick={() => {
                            removeNote(key);
                            setDeleting(null);
                          }}
                        >
                          {t('mypage.visits.delete')}
                        </button>
                      </div>
                    ) : (
                      <div className="visit-actions">
                        <button
                          type="button"
                          className="visit-button"
                          onClick={() => {
                            setDeleting(null);
                            setEditing(key);
                          }}
                        >
                          {t('mypage.visits.edit')}
                        </button>
                        <button type="button" className="visit-button" onClick={() => setDeleting(key)}>
                          {t('mypage.visits.delete')}
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            </article>
          );
        })}
        <p className="visit-device-note">{t('mypage.visits.deviceNote')}</p>
      </section>

      <LegalLinks />
    </div>
  );
}
