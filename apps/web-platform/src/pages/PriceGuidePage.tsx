import { useCallback, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { FilterGrid } from '../features/hospital/FilterGrid';
import { DEPARTMENTS } from '../features/hospital/filters';
import { ProcedureCard } from '../features/price-info/ProcedureCard';
import { ProcedureHospitals } from '../features/price-info/ProcedureHospitals';
import { PROCEDURE_CATEGORIES, type Procedure } from '../features/price-info/procedures';
import { useCurrency } from '../components/currency';
import { useExchangeRates, useFallbackRate } from '../components/exchangeRates';
import { useLoadMore } from '../components/useLoadMore';

const PAGE_SIZE = 12;
// 시술 이름 찾기: 띄어쓰기·대소문자 무시 (챗봇 가격 버튼이 ?q=필러 처럼 연다, 2026-11-26)
const norm = (s: string) => s.toLowerCase().replace(/\s+/g, '');

export function PriceGuidePage() {
  const { t, i18n } = useTranslation();
  const [params, setParams] = useSearchParams();
  const dept = params.get('dept');
  // 누른 시술 → 이 시술을 하는 병원 창
  const [opened, setOpened] = useState<Procedure | null>(null);
  const closeOpened = useCallback(() => setOpened(null), []);
  const q = params.get('q')?.trim() || null;
  const { currency } = useCurrency();
  // 원화가 아닌 통화를 골랐을 때만 환율을 받는다
  const fx = useExchangeRates(currency !== 'KRW');
  const backendRate = currency !== 'KRW' && fx.status === 'ready' ? fx.data.rates[currency] : undefined;
  // 백엔드에 그 통화가 없으면(지금은 JPY) ECB 참고 환율로 임시 환산
  const needFallback = currency !== 'KRW' && (fx.status === 'error' || (fx.status === 'ready' && !backendRate));
  const fb = useFallbackRate(currency, needFallback);
  const fallbackRate = needFallback && fb.status === 'ready' ? fb.data.rate : undefined;
  const rate = backendRate ?? fallbackRate;

  // 'YYYY-MM-DD' → 화면 언어 날짜 (시간대 영향 없게 UTC 정오로). 형식이 다르면(예전 응답 캐시 등) 빈 값
  const day = (d: string | undefined) => {
    const t = d && /^\d{4}-\d{2}-\d{2}$/.test(d) ? new Date(`${d}T12:00:00Z`) : null;
    return t ? new Intl.DateTimeFormat(i18n.language, { dateStyle: 'medium', timeZone: 'UTC' }).format(t) : '';
  };
  const fxDate = fx.status === 'ready' ? day(fx.data.applied_on) : '';

  // 진료과를 바꾸면 시술 이름 찾기는 풀린다
  const selectDept = (v: string | null) => setParams(v ? { dept: v } : {}, { replace: true });
  const clearSearch = () => setParams(dept ? { dept } : {}, { replace: true });

  // 진료과 순서대로 카드를 한 줄로 세운 뒤 보여 줄 개수만큼 자르고, 다시 진료과별로 묶음
  const sections = DEPARTMENTS.filter((d) => !dept || d === dept);
  const all = sections.flatMap((d) =>
    PROCEDURE_CATEGORIES.filter((c) => c.dept === d).flatMap((c) => c.items.map((p) => ({ d, c, p }))),
  );
  // q가 있으면 시술 이름(한·영)이나 묶음 이름에 그 말이 들어간 것만. 하나도 없으면 전체를 보여 주고 안내
  const matched = q ? all.filter(({ c, p }) => [p.ko, p.en, c.ko, c.en].some((s) => norm(s).includes(norm(q)))) : all;
  const cards = matched.length ? matched : all;
  // 처음부터 무한 스크롤 (시술 이름·진료과가 바뀌면 처음으로)
  const { shown, sentinelRef, autoLoading } = useLoadMore(cards.length, PAGE_SIZE, `${dept ?? ''}|${q ?? ''}`, true);
  const visibleCards = cards.slice(0, shown);

  return (
    <div className="hospitals-page">
      <h1 className="visually-hidden">{t('nav.prices')}</h1>
      <FilterGrid
        label={t('dept.label')}
        allLabel={t('dept.all')}
        options={DEPARTMENTS.map((d) => ({ value: d, label: t(`dept.${d}`) }))}
        selected={dept}
        onSelect={selectDept}
      />
      {q && (
        <p className="price-search">
          {matched.length ? t('prices.searchResult', { q, count: matched.length }) : t('prices.noResult', { q })}{' '}
          <button type="button" className="price-search-clear" onClick={clearSearch}>
            {t('prices.clearSearch')}
          </button>
        </p>
      )}

      {sections
        .filter((d) => visibleCards.some((v) => v.d === d))
        .map((d) => (
          <section key={d} className="procedure-section">
            <h2 className="procedure-dept">{t(`dept.${d}`)}</h2>
            <div className="procedure-grid">
              {visibleCards
                .filter((v) => v.d === d)
                .map(({ c, p }) => (
                  <ProcedureCard key={p.ko} procedure={p} category={c} currency={currency} rate={rate} onOpen={() => setOpened(p)} />
                ))}
            </div>
          </section>
        ))}
      {opened && <ProcedureHospitals procedure={opened} onClose={closeOpened} />}
      {autoLoading && <div ref={sentinelRef} className="load-more-sentinel" aria-hidden="true" />}

      <p className="detail-source">{t('prices.notice')}</p>
      {currency !== 'KRW' && fx.status === 'ready' && backendRate && fxDate && (
        <p className="detail-source">
          {t('prices.fxNotice', {
            applied: fxDate,
            base: day(fx.data.base_date),
            hour: fx.data.switch_hour_kst,
          })}{' '}
          <a href={fx.data.provider.url} target="_blank" rel="noopener noreferrer">
            {t('prices.fxProvider')}
          </a>
        </p>
      )}
      {fallbackRate && fb.status === 'ready' && (
        <p className="detail-source">
          {t('prices.fxReference', { date: day(fb.data.date) })}{' '}
          <a href={fb.data.provider.url} target="_blank" rel="noopener noreferrer">
            {fb.data.provider.name}
          </a>
        </p>
      )}
      {needFallback && fb.status === 'error' && <p className="detail-source">{t('prices.fxFallback')}</p>}
    </div>
  );
}
