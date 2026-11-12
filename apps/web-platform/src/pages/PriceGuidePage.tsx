import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { FilterGrid } from '../features/hospital/FilterGrid';
import { DEPARTMENTS } from '../features/hospital/filters';
import { ProcedureCard } from '../features/price-info/ProcedureCard';
import { PROCEDURE_CATEGORIES } from '../features/price-info/procedures';
import { useCurrency } from '../components/currency';
import { useExchangeRates } from '../components/exchangeRates';

export function PriceGuidePage() {
  const { t, i18n } = useTranslation();
  const [params, setParams] = useSearchParams();
  const dept = params.get('dept');
  const { currency } = useCurrency();
  // 원화가 아닌 통화를 골랐을 때만 환율을 받는다
  const fx = useExchangeRates(currency !== 'KRW');
  const rate = currency !== 'KRW' && fx.status === 'ready' ? fx.data.rates[currency] : undefined;

  // 'YYYY-MM-DD' → 화면 언어 날짜 (시간대 영향 없게 UTC 정오로). 형식이 다르면(예전 응답 캐시 등) 빈 값
  const day = (d: string | undefined) => {
    const t = d && /^\d{4}-\d{2}-\d{2}$/.test(d) ? new Date(`${d}T12:00:00Z`) : null;
    return t ? new Intl.DateTimeFormat(i18n.language, { dateStyle: 'medium', timeZone: 'UTC' }).format(t) : '';
  };
  const fxDate = fx.status === 'ready' ? day(fx.data.applied_on) : '';

  const selectDept = (v: string | null) => setParams(v ? { dept: v } : {}, { replace: true });

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

      {DEPARTMENTS.filter((d) => !dept || d === dept).map((d) => (
        <section key={d} className="procedure-section">
          <h2 className="procedure-dept">{t(`dept.${d}`)}</h2>
          <div className="procedure-grid">
            {PROCEDURE_CATEGORIES.filter((c) => c.dept === d).flatMap((c) =>
              c.items.map((p) => (
                <ProcedureCard key={p.ko} procedure={p} category={c} currency={currency} rate={rate} />
              )),
            )}
          </div>
        </section>
      ))}

      <p className="detail-source">{t('prices.notice')}</p>
      {currency !== 'KRW' && fx.status === 'ready' && rate && fxDate && (
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
      {currency !== 'KRW' && (fx.status === 'error' || (fx.status === 'ready' && !rate)) && (
        <p className="detail-source">{t('prices.fxFallback')}</p>
      )}
    </div>
  );
}
