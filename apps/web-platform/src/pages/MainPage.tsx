import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AdSlot } from '../components/AdSlot';
import { DepartmentFilter } from '../features/map/DepartmentFilter';
import { HospitalMap } from '../features/map/HospitalMap';
import { useHospitals } from '../features/hospital/useHospitals';
import type { DepartmentKey } from '../features/hospital/types';

export function MainPage() {
  const { t } = useTranslation();
  const state = useHospitals();
  const [dept, setDept] = useState<DepartmentKey | null>(null);

  const visible = useMemo(() => {
    if (state.status !== 'ready') return [];
    const items = state.data.items;
    return dept ? items.filter((h) => h.depts.includes(dept)) : items;
  }, [state, dept]);

  return (
    <div className="main-page">
      <section className="map-card" aria-labelledby="map-title">
        <div className="map-card-head">
          <h1 id="map-title">{t('map.title')}</h1>
          {state.status === 'ready' && (
            <span className="map-count">{t('map.count', { count: visible.length })}</span>
          )}
        </div>
        {state.status === 'loading' && <p className="map-status">{t('map.loading')}</p>}
        {state.status === 'error' && <p className="map-status">{t('map.error')}</p>}
        {state.status === 'ready' && (
          <HospitalMap hospitals={visible} fetchedAt={state.data.meta.fetchedAt} />
        )}
      </section>

      <DepartmentFilter selected={dept} onSelect={setDept} />

      <div className="ad-row">
        <AdSlot className="ad-wide" />
        <AdSlot />
      </div>
    </div>
  );
}
