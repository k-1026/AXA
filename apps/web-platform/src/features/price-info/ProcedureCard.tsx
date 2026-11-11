import { useTranslation } from 'react-i18next';
import type { Procedure, ProcedureCategory } from './procedures';

interface Props {
  procedure: Procedure;
  category: ProcedureCategory;
}

export function ProcedureCard({ procedure: p, category }: Props) {
  const { t, i18n } = useTranslation();
  // 병원 이름과 같은 규칙: 한국어 외 모든 언어는 영어로 통일
  const label = (x: { ko: string; en: string }) => (i18n.language === 'ko' ? x.ko : x.en);

  return (
    <article className="procedure-card">
      {/* 팀에서 만든 일러스트만 쓴다 (전후 사진은 쓰지 않음, docs/compliance.md). 없으면 빈 자리 */}
      <div className={`hospital-photo procedure-photo ${p.image ? 'has-image' : ''}`} aria-hidden="true">
        {p.image && <img src={`/procedures/${p.image}.jpg`} alt="" loading="lazy" />}
      </div>
      <p className="hospital-type">{label(category)}</p>
      <h2>{label(p)}</h2>
      <p className={p.price ? 'procedure-price' : 'procedure-price is-pending'}>
        {p.price
          ? t('prices.range', {
              min: p.price.min.toLocaleString('en-US'),
              max: p.price.max.toLocaleString('en-US'),
            })
          : t('prices.pending')}
      </p>
    </article>
  );
}
