import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useSavedHospitals } from '../hospital/savedHospitals';
import { ArrowRightIcon, GlobeIcon, HeartIcon, PinIcon } from './icons';
import { SAVED_DEPTS, type Localized, type SavedHospital } from './sampleData';

// 저장한 병원 카드. 예시 병원의 하트는 화면 안에서만 토글, 실제로 찜한 병원은 누르면 찜 해제
export function SavedHospitalCard({ hospital: h }: { hospital: SavedHospital }) {
  const { t, i18n } = useTranslation();
  const label = (x: Localized) => (i18n.language === 'ko' ? x.ko : x.en);
  const [sampleSaved, setSampleSaved] = useState(true);
  const { toggle } = useSavedHospitals();
  const saved = h.real || sampleSaved;
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
              {!h.real && <span className="mp-saved-sample">{t('mypage.saved.sampleHospital')}</span>}
            </p>
            {i18n.language === 'ko' && <p className="mp-saved-name-en">{h.name.en}</p>}
          </div>
          <button
            type="button"
            className={saved ? 'mp-heart is-saved' : 'mp-heart'}
            aria-pressed={saved}
            onClick={() => (h.real ? toggle(h.id) : setSampleSaved(!sampleSaved))}
          >
            <span className="mp-heart-circle">
              <HeartIcon filled={saved} />
            </span>
            {t(saved ? 'mypage.saved.saved' : 'mypage.saved.save')}
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
