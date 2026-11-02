import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { FilterGrid } from '../features/hospital/FilterGrid';
import { DEPARTMENTS } from '../features/hospital/filters';
import { ProcedureCard } from '../features/price-info/ProcedureCard';
import { PROCEDURE_CATEGORIES } from '../features/price-info/procedures';

export function PriceGuidePage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const dept = params.get('dept');

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
              c.items.map((p) => <ProcedureCard key={p.ko} procedure={p} category={c} />),
            )}
          </div>
        </section>
      ))}

      <p className="detail-source">{t('prices.notice')}</p>
    </div>
  );
}
