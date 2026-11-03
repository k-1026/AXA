import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { instagramHandle, useHospitalName } from './name';
import type { Hospital } from './types';

export function HospitalCard({ hospital: h }: { hospital: Hospital }) {
  const { t } = useTranslation();
  const nameOf = useHospitalName();

  return (
    <article className="hospital-card">
      {/* 병원 사진 데이터가 아직 없어서 빈 자리 */}
      <div className="hospital-photo" aria-hidden="true" />
      <div className="hospital-card-body">
        <p className="hospital-type">{t(`hospitalType.${h.type}`, { defaultValue: h.type })}</p>
        <h2>
          {/* 카드 전체를 덮는 링크 (CSS ::after) */}
          <Link
            to={`/hospitals/${encodeURIComponent(h.id)}`}
            state={{ fromList: true }}
            className="card-link"
          >
            {nameOf(h)}
          </Link>
        </h2>
        <dl className="hospital-facts">
          <dt>{t('popup.addr')}</dt>
          <dd>{h.addr}</dd>
          <dt>{t('popup.tel')}</dt>
          <dd>{h.tel && <a href={`tel:${h.tel}`}>{h.tel}</a>}</dd>
          <dt>{t('hospital.homepage')}</dt>
          <dd>
            {h.url && (
              <a href={h.url} target="_blank" rel="noopener noreferrer">
                {h.url.replace(/^https?:\/\//, '').replace(/\/$/, '')}
              </a>
            )}
          </dd>
          <dt>{t('hospital.instagram')}</dt>
          <dd>
            {h.instagram && (
              <a href={h.instagram} target="_blank" rel="noopener noreferrer">
                {instagramHandle(h.instagram)}
              </a>
            )}
          </dd>
        </dl>
      </div>
    </article>
  );
}
