import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LegalLinks } from '../features/legal/LegalLinks';
import { useHospitalName } from '../features/hospital/name';
import { useHospitals } from '../features/hospital/useHospitals';
import { VisitForm } from '../features/mypage/VisitForm';
import { ArrowLeftIcon, LockIcon } from '../features/mypage/icons';
import { useVisitLog } from '../features/mypage/visitLog';

// 마이페이지 > 방문 기록. 본인만 쓰고 보는 다이어리 (공개 후기 아님, 병원 화면에 표시하지 않음)
export function VisitsPage() {
  const { t } = useTranslation();
  const nameOf = useHospitalName();
  const state = useHospitals();
  const { visits, add, update, remove } = useVisitLog();
  const [editing, setEditing] = useState<string | null>(null);

  const hospitals = state.status === 'ready' ? state.data.items : [];
  const sorted = [...visits].sort(
    (a, b) => b.date.localeCompare(a.date) || b.createdAt.localeCompare(a.createdAt),
  );

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
            {t('mypage.visits.title')} <span>{visits.length}</span>
          </h1>
          <p className="mp-greeting-sub">{t('mypage.visits.subtitle')}</p>
        </div>
        <span className="visit-private">
          <LockIcon />
          {t('mypage.visits.private')}
        </span>
      </div>

      <section className="mp-card visit-card">
        <h2>{t('mypage.visits.formTitle')}</h2>
        <VisitForm hospitals={hospitals} onSubmit={add} />
        <p className="visit-device-note">{t('mypage.visits.deviceNote')}</p>
      </section>

      <section className="mp-saved-list">
        <h2 className="visit-list-title">{t('mypage.visits.listTitle')}</h2>
        {sorted.length === 0 && <p className="mp-saved-empty">{t('mypage.visits.none')}</p>}
        {sorted.map((v) => {
          const hospital = hospitals.find((h) => h.id === v.hospitalId);
          return (
            <article key={v.id} className="mp-card visit-card">
              {editing === v.id ? (
                <VisitForm
                  hospitals={hospitals}
                  initial={v}
                  onSubmit={(input) => {
                    update(v.id, input);
                    setEditing(null);
                  }}
                  onCancel={() => setEditing(null)}
                />
              ) : (
                <>
                  <div className="visit-head">
                    <h3>
                      {hospital ? (
                        <Link to={`/hospitals/${encodeURIComponent(hospital.id)}`}>{nameOf(hospital)}</Link>
                      ) : (
                        v.hospitalName
                      )}
                    </h3>
                    <time dateTime={v.date}>{v.date}</time>
                  </div>
                  <p className="visit-note">{v.note}</p>
                  <div className="visit-actions">
                    <button type="button" className="visit-button" onClick={() => setEditing(v.id)}>
                      {t('mypage.visits.edit')}
                    </button>
                    <button
                      type="button"
                      className="visit-button"
                      onClick={() => {
                        if (window.confirm(t('mypage.visits.deleteConfirm'))) remove(v.id);
                      }}
                    >
                      {t('mypage.visits.delete')}
                    </button>
                  </div>
                </>
              )}
            </article>
          );
        })}
      </section>

      <LegalLinks />
    </div>
  );
}
