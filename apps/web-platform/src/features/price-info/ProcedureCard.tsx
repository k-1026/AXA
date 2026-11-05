import { useTranslation } from 'react-i18next';
import type { Currency } from '../../components/currency';
import { formatConverted } from '../../components/exchangeRates';
import type { Procedure, ProcedureCategory } from './procedures';

interface Props {
  procedure: Procedure;
  category: ProcedureCategory;
  currency: Currency;
  rate?: number; // 1원 = rate. 없으면(원화 선택·환율 못 받음) 원화로만
}

export function ProcedureCard({ procedure: p, category, currency, rate }: Props) {
  const { t, i18n } = useTranslation();
  // 병원 이름과 같은 규칙: 한국어 외 모든 언어는 영어로 통일
  const label = (x: { ko: string; en: string }) => (i18n.language === 'ko' ? x.ko : x.en);
  // 영어로 보일 때는 영어 글꼴·하이픈 줄바꿈 (중국어 글꼴은 영문 폭이 넓어 좁은 카드에서 단어가 잘림)
  const labelLang = i18n.language === 'ko' ? undefined : 'en';

  const krw = p.price && {
    min: p.price.min.toLocaleString('en-US'),
    max: p.price.max.toLocaleString('en-US'),
  };
  const converted =
    p.price && currency !== 'KRW' && rate
      ? {
          min: formatConverted(p.price.min, currency, rate, i18n.language),
          max: formatConverted(p.price.max, currency, rate, i18n.language),
        }
      : null;

  return (
    <article className="procedure-card">
      {/* 팀에서 만든 일러스트만 쓴다 (전후 사진은 쓰지 않음, docs/compliance.md). 없으면 빈 자리 */}
      <div className={`hospital-photo procedure-photo ${p.image ? 'has-image' : ''}`} aria-hidden="true">
        {p.image && <img src={`/procedures/${p.image}`} alt="" loading="lazy" />}
      </div>
      <p className="hospital-type" lang={labelLang}>{label(category)}</p>
      <h2 lang={labelLang}>{label(p)}</h2>
      {!krw ? (
        <p className="procedure-price is-pending">{t('prices.pending')}</p>
      ) : converted ? (
        <>
          <p className="procedure-price">{t('prices.approx', converted)}</p>
          {/* 실제 비용은 원화 기준이라 원화도 같이 */}
          <p className="procedure-price-krw">{t('prices.krwNote', krw)}</p>
        </>
      ) : (
        <p className="procedure-price">{t('prices.range', krw)}</p>
      )}
    </article>
  );
}
