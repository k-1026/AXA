import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { HospitalThumb } from '../consult/HospitalThumb';
import { HospitalAddress } from '../hospital/HospitalAddress';
import { useHospitalName } from '../hospital/name';
import { useHospitals } from '../hospital/useHospitals';
import { useLocalized } from '../../lib/common';
import { PROCEDURE_HOSPITALS, PROCEDURE_HOSPITALS_DATE, PROCEDURE_HOSPITALS_WEB_DATE } from './procedureHospitalData';
import type { Procedure } from './procedures';

// 가격 가이드에서 시술을 누르면 "이 시술을 하는 병원"을 보여 주는 창 (2026-11-27)
// 근거: 그 시술 가격을 심평원에 공개한 병원 + 홈페이지 진료 안내에 그 시술이 있는 병원 (procedureHospitalData.ts, data/etl/procedure_hospitals.py)
// 공개 자료가 없는 시술(미용 시술 등)은 목록 없이 "준비 중" — 진료과 전체 병원을 대신 보여 주지 않는다
export function ProcedureHospitals({ procedure, onClose }: { procedure: Procedure; onClose: () => void }) {
  const { t } = useTranslation();
  const label = useLocalized();
  const hospitalName = useHospitalName();
  const state = useHospitals();
  const closeRef = useRef<HTMLButtonElement>(null);
  const entry = PROCEDURE_HOSPITALS[procedure.ko];

  // Esc로 닫기 + 열릴 때 닫기 버튼에 초점
  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const all = state.status === 'ready' ? state.data.items : [];
  const hospitals = (entry ?? []).flatMap((s) => {
    const h = all.find((x) => x.id === s.id);
    return h ? [{ h, s }] : [];
  });
  const title = label(procedure);

  return (
    <div className="mp-dialog-backdrop" onClick={onClose}>
      <div className="mp-dialog proc-hosp" role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <div className="proc-hosp-head">
          <h2>{title}</h2>
          <button ref={closeRef} type="button" className="proc-hosp-close" onClick={onClose} aria-label={t('prices.hospitals.close')}>
            ×
          </button>
        </div>

        {!entry ? (
          <p className="proc-hosp-empty">{t('prices.hospitals.none')}</p>
        ) : state.status === 'loading' ? (
          <p className="proc-hosp-empty">{t('map.loading')}</p>
        ) : (
          <>
            <p className="proc-hosp-count">{t('prices.hospitals.count', { count: hospitals.length })}</p>
            <ul className="proc-hosp-list">
              {hospitals.map(({ h, s }) => (
                <li key={h.id} className="proc-hosp-row">
                  <Link to={`/hospitals/${encodeURIComponent(h.id)}`} className="proc-hosp-item">
                    <HospitalThumb photo={h.photo} />
                    <span className="proc-hosp-text">
                      <strong>{hospitalName(h)}</strong>
                      <small>
                        <HospitalAddress addr={h.addr} original={false} />
                      </small>
                    </span>
                  </Link>
                  {/* 근거 표시: 심평원 가격 공개 / 홈페이지 안내 (출처 쪽 링크) */}
                  {s.src === 'hira' ? (
                    <span className="proc-hosp-src">{t('prices.hospitals.srcHira')}</span>
                  ) : (
                    <a className="proc-hosp-src is-web" href={s.url} target="_blank" rel="noopener noreferrer">
                      {t('prices.hospitals.srcWeb')} ↗
                    </a>
                  )}
                </li>
              ))}
            </ul>
            <p className="proc-hosp-note">{t('prices.hospitals.basis', { date: PROCEDURE_HOSPITALS_DATE, webDate: PROCEDURE_HOSPITALS_WEB_DATE })}</p>
          </>
        )}
      </div>
    </div>
  );
}
