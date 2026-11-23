import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AdRotator, type Ad } from '../components/AdRotator';
import { DepartmentFilter } from '../features/map/DepartmentFilter';
import { HospitalMap } from '../features/map/HospitalMap';
import { HospitalSearch } from '../features/map/HospitalSearch';
import { useHospitals } from '../features/hospital/useHospitals';
import type { DepartmentKey, Hospital } from '../features/hospital/types';
import { onMap } from '../features/hospital/filters';

// 메인 하단 광고 배너 (비의료 일반 광고주만 · 5초마다 돌아감)
const ADS: Ad[] = [
  { image: '/ads/hanbang-skincare.webp', alt: 'Yakryeongsi — Hanbang skincare. Rooted in Daegu.' },
  { image: '/ads/biseulsan-ice-festival.webp', alt: 'Biseulsan Ice Festival — Daegu, on ice. Dalseong, Daegu' },
  { image: '/ads/eworld-daegu.webp', alt: "E-World Daegu — Your Daegu play date. Let's play" },
  { image: '/ads/daegu-chimac-festival.webp', alt: 'Daegu Chimac Festival — Chicken. Beer. Daegu. Taste the fun' },
];

export function MainPage() {
  const { t } = useTranslation();
  const state = useHospitals();
  const [dept, setDept] = useState<DepartmentKey | null>(null);
  // 병원 이름 검색 결과. 있으면 그 병원만 지도에 표시하고 확대
  const [found, setFound] = useState<Hospital[] | null>(null);
  const [searchKey, setSearchKey] = useState(0);

  const search = (result: Hospital[] | null) => {
    setFound(result);
    if (result) setDept(null);
  };

  // 진료과를 고르면 검색은 해제
  const selectDept = (d: DepartmentKey | null) => {
    setDept(d);
    if (found) {
      setFound(null);
      setSearchKey((k) => k + 1);
    }
  };

  // 지도는 서비스 진료과(피부·성형·내과·안과)가 있는 병원만 — 한의원·치과 등 '기타'만 있는 병원은 뺌
  const mapItems = useMemo(() => (state.status === 'ready' ? state.data.items.filter(onMap) : []), [state]);

  const visible = useMemo(() => {
    if (state.status !== 'ready') return [];
    if (found) return found;
    const items = mapItems;
    return dept ? items.filter((h) => h.depts.includes(dept)) : items;
  }, [mapItems, dept, found]);

  return (
    <div className="main-page">
      <section className="map-card" aria-labelledby="map-title">
        <div className="map-card-head">
          <h1 id="map-title">{t('map.title')}</h1>
          {/* 개수는 제목 옆, 검색창은 오른쪽 끝 고정 (개수 글자 길이에 따라 검색창이 밀리지 않게) */}
          {state.status === 'ready' && (
            <span className="map-count">{t('map.count', { count: visible.length })}</span>
          )}
          {state.status === 'ready' && (
            <HospitalSearch key={searchKey} hospitals={mapItems} onSearch={search} />
          )}
        </div>
        {state.status === 'loading' && <p className="map-status">{t('map.loading')}</p>}
        {state.status === 'error' && <p className="map-status">{t('map.error')}</p>}
        {state.status === 'ready' && (
          <HospitalMap hospitals={visible} fetchedAt={state.data.meta.fetchedAt} selectedDept={dept} focus={found} />
        )}
      </section>

      <DepartmentFilter selected={dept} onSelect={selectDept} />

      <AdRotator ads={ADS} />
    </div>
  );
}
