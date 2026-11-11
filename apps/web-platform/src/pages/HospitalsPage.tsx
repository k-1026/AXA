import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { FilterGrid } from '../features/hospital/FilterGrid';
import { HospitalCard } from '../features/hospital/HospitalCard';
import { DEPARTMENTS, DISTRICTS } from '../features/hospital/filters';
import { useHospitals } from '../features/hospital/useHospitals';
import type { DepartmentKey } from '../features/hospital/types';

const PAGE_SIZE = 24;

export function HospitalsPage() {
  const { t } = useTranslation();
  const state = useHospitals();
  // 필터는 주소(?dept=&district=)에 저장 → 상세에서 뒤로 와도 유지
  const [params, setParams] = useSearchParams();
  const dept = params.get('dept') as DepartmentKey | null;
  const district = params.get('district');
  const [shown, setShown] = useState(PAGE_SIZE);

  // 데이터가 이미 한국어 가나다순이라 언어와 상관없이 순서 그대로
  const visible = useMemo(() => {
    if (state.status !== 'ready') return [];
    return state.data.items.filter(
      (h) => (!dept || h.depts.includes(dept)) && (!district || h.district === district),
    );
  }, [state, dept, district]);

  const setFilter = (key: 'dept' | 'district') => (v: string | null) => {
    const next = new URLSearchParams(params);
    if (v) next.set(key, v);
    else next.delete(key);
    setParams(next, { replace: true });
    setShown(PAGE_SIZE);
  };
  const changeDept = setFilter('dept');
  const changeDistrict = setFilter('district');

  return (
    <div className="hospitals-page">
      <div className="filters">
        <FilterGrid
          label={t('dept.label')}
          allLabel={t('dept.all')}
          options={DEPARTMENTS.map((d) => ({ value: d, label: t(`dept.${d}`) }))}
          selected={dept}
          onSelect={changeDept}
        />
        <FilterGrid
          label={t('district.label')}
          allLabel={t('district.all')}
          options={DISTRICTS.map((d) => ({ value: d, label: t(`district.${d}`) }))}
          selected={district}
          onSelect={changeDistrict}
        />
      </div>

      {state.status === 'loading' && <p className="list-status">{t('map.loading')}</p>}
      {state.status === 'error' && <p className="list-status">{t('map.error')}</p>}
      {state.status === 'ready' && (
        <>
          <p className="list-count">{t('map.count', { count: visible.length })}</p>
          {visible.length === 0 ? (
            <p className="list-status">{t('hospital.empty')}</p>
          ) : (
            <div className="hospital-grid">
              {visible.slice(0, shown).map((h) => (
                <HospitalCard key={h.id} hospital={h} />
              ))}
            </div>
          )}
          {shown < visible.length && (
            <button type="button" className="more-button" onClick={() => setShown(shown + PAGE_SIZE)}>
              {t('hospital.more', { count: visible.length - shown })}
            </button>
          )}
        </>
      )}
    </div>
  );
}
