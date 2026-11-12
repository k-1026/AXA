import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useSavedHospitals } from '../hospital/savedHospitals';
import { ArrowRightIcon, GlobeIcon, HeartIcon, PinIcon } from './icons';
import { useLocalized } from '../../lib/common';
import { SAVED_DEPTS, type SavedHospital } from './sampleData';

// 저장한 병원 카드. 하트를 누르면 찜 해제
export function SavedHospitalCard({ hospital: h }: { hospital: SavedHospital }) {
  const { t, i18n } = useTranslation();
  const label = useLocalized();
  const { toggle } = useSavedHospitals();
  const dept = SAVED_DEPTS.find((d) => d.key === h.dept)!;

  return (
    <article className="mp-card mp-saved-card">
      {/* 병원 사진은 나중에 첨부 (전후 사진은 쓰지 않음, docs/compliance.md) */}
      <div className="mp-saved-photo">{t('mypage.saved.photo')}</div>

      <div className="mp-saved-body">
        <div className="mp-saved-head">
          <div>
            <p className="mp-saved-name">
              <span className={`mp-tag dept-${h.dept}`}>{label(dept.label)}</span>
              <strong>{label(h.name)}</strong>
            </p>
            {i18n.language === 'ko' && <p className="mp-saved-name-en">{h.name.en}</p>}
          </div>
          <button
            type="button"
            className="mp-heart is-saved"
            aria-pressed="true"
            onClick={() => toggle(h.id)}
          >
            <span className="mp-heart-circle">
              <HeartIcon filled />
            </span>
            {t('mypage.saved.saved')}
          </button>
        </div>

        <div className="mp-saved-meta">
          <span className="mp-saved-area">
            <PinIcon />
            {label(h.area)}
          </span>
          <ul className="mp-saved-chips">
            {h.treatments.map((x) => (
              <li key={x.ko}>{label(x)}</li>
            ))}
          </ul>
          {h.languages.length > 0 && (
            <span className="mp-saved-lang">
              <GlobeIcon />
              {t('mypage.saved.languages')}
              <strong>{h.languages.map(label).join(' · ')}</strong>
            </span>
          )}
        </div>

        <div className="mp-saved-price">
          {h.prices.length > 0 && (
            <>
              <p className="mp-saved-price-title">{t('mypage.saved.priceTitle')}</p>
              <ul className="mp-saved-price-list">
                {h.prices.map((p) => (
                  <li key={p.name.ko}>
                    <span>{label(p.name)}</span>
                    <span className={p.range ? '' : 'is-pending'}>{p.range ?? t('prices.pending')}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
          <Link to={h.detailTo} className="mp-saved-detail">
            {t('mypage.saved.detail')}
            <ArrowRightIcon />
          </Link>
          {h.prices.length > 0 && <p className="mp-saved-price-note">{t('mypage.saved.priceNote')}</p>}
        </div>
      </div>
    </article>
  );
}
