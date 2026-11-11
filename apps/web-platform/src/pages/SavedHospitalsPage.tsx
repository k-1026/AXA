import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { SavedHospitalCard } from '../features/mypage/SavedHospitalCard';
import { ArrowLeftIcon } from '../features/mypage/icons';
import { SAVED_DEPTS, type SavedDept } from '../features/mypage/sampleData';
import { useMyPageData } from '../features/mypage/useMyPageData';
import { LegalLinks } from '../features/legal/LegalLinks';

type Sort = 'recent' | 'name';

// 마이페이지 > 저장한 병원. 사용자가 직접 저장한 병원만 보여준다 (순위·추천 없음)
export function SavedHospitalsPage() {
  const { t, i18n } = useTranslation();
  const [dept, setDept] = useState<SavedDept | null>(null);
  const [sort, setSort] = useState<Sort>('recent');
  const lang = i18n.language === 'ko' ? 'ko' : 'en';
  const { saved } = useMyPageData();

  const items = saved.filter((h) => !dept || h.dept === dept).sort((a, b) =>
    sort === 'recent' ? b.savedAt.localeCompare(a.savedAt) : a.name[lang].localeCompare(b.name[lang], lang),
  );

  return (
    <div className="mypage">
      <nav className="mp-breadcrumb" aria-label="breadcrumb">
        <Link to="/">{t('mypage.home')}</Link>
        <span aria-hidden="true">/</span>
        <Link to="/mypage">{t('nav.mypage')}</Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page" className="is-current">
          {t('mypage.saved.title')}
        </span>
      </nav>

      <div className="mp-saved-top">
        <div>
          <Link to="/mypage" className="mp-back">
            <ArrowLeftIcon />
            {t('nav.mypage')}
          </Link>
          <h1 className="mp-saved-title">
            {t('mypage.saved.title')} <span>{saved.length}</span>
          </h1>
          <p className="mp-greeting-sub">{t('mypage.saved.subtitle')}</p>
        </div>
        <select
          className="mp-sort"
          value={sort}
          onChange={(e) => setSort(e.target.value as Sort)}
          aria-label={t('mypage.saved.sortLabel')}
        >
          <option value="recent">{t('mypage.saved.sortRecent')}</option>
          <option value="name">{t('mypage.saved.sortName')}</option>
        </select>
      </div>

      <div className="mp-saved-filter-row">
        <div className="mp-pills" role="group" aria-label={t('dept.label')}>
          <button type="button" aria-pressed={!dept} onClick={() => setDept(null)}>
            {t('dept.all')}
          </button>
          {SAVED_DEPTS.map((d) => (
            <button key={d.key} type="button" aria-pressed={dept === d.key} onClick={() => setDept(d.key)}>
              {d.label[lang]}
            </button>
          ))}
        </div>
      </div>

      <div className="mp-saved-list">
        {items.length ? (
          items.map((h) => <SavedHospitalCard key={h.id} hospital={h} />)
        ) : (
          <p className="mp-saved-empty">{t(saved.length ? 'mypage.saved.empty' : 'mypage.saved.none')}</p>
        )}
      </div>


      <LegalLinks />
    </div>
  );
}
