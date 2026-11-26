import { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { HospitalCard } from '../features/hospital/HospitalCard';
import { HospitalFilterBar } from '../features/hospital/HospitalFilterBar';
import { EMPTY_FILTERS, matches, readFilters, writeFilters, type SearchFilters } from '../features/hospital/searchFilters';
import { useHospitals } from '../features/hospital/useHospitals';
import { useLoadMore } from '../components/useLoadMore';

const PAGE_SIZE = 24;

export function HospitalsPage() {
  const { t } = useTranslation();
  const state = useHospitals();
  // 적용된 조건은 주소(?dept=a,b&district=중구,수성구&lang=en)에 저장 → 상세에서 뒤로 와도 유지
  const [params, setParams] = useSearchParams();
  const applied = useMemo(() => readFilters(params), [params]);
  const key = params.toString();

  const items = useMemo(() => (state.status === 'ready' ? state.data.items : []), [state]);

  // 데이터가 이미 한국어 가나다순이라 언어와 상관없이 순서 그대로. 같은 id는 한 번만
  const visible = useMemo(() => {
    const seen = new Set<string>();
    const out = items.filter((h) => {
      if (seen.has(h.id) || !matches(h, applied)) return false;
      seen.add(h.id);
      return true;
    });
    // 시연용 예시 병원(DEMO-…)은 가나다순 중간에 섞이지 않게 맨 위로 (나머지 순서는 그대로)
    const isDemo = (h: { id: string }) => h.id.startsWith('DEMO-');
    return [...out.filter(isDemo), ...out.filter((h) => !isDemo(h))];
  }, [items, applied]);
  const { shown, showButton, more, sentinelRef, autoLoading } = useLoadMore(visible.length, PAGE_SIZE, key);

  const apply = (f: SearchFilters) => setParams(writeFilters(params, f), { replace: true });

  return (
    <div className="hospitals-page">
      <HospitalFilterBar hospitals={items} applied={applied} onApply={apply} />

      {state.status === 'loading' && <p className="list-status">{t('map.loading')}</p>}
      {state.status === 'error' && <p className="list-status">{t('map.error')}</p>}
      {state.status === 'ready' && (
        <>
          <p className="list-count">{t('map.count', { count: visible.length })}</p>
          {visible.length === 0 ? (
            <div className="list-empty">
              <p className="list-status">{t('filter.noResult')}</p>
              <button type="button" className="hf-apply" onClick={() => apply(EMPTY_FILTERS)}>
                {t('filter.reset')}
              </button>
            </div>
          ) : (
            <div className="hospital-grid">
              {visible.slice(0, shown).map((h) => (
                <HospitalCard key={h.id} hospital={h} />
              ))}
            </div>
          )}
          {showButton && (
            <button type="button" className="more-button" onClick={more}>
              {t('hospital.more', { count: visible.length - shown })}
            </button>
          )}
          {autoLoading && <div ref={sentinelRef} className="load-more-sentinel" aria-hidden="true" />}
        </>
      )}
    </div>
  );
}
