import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LegalLinks } from '../features/legal/LegalLinks';

// 가이드북: 외국인 환자를 위한 메디대구 이용 방법 (로그인 없이 누구나, 2026-11-26)
// 구성: 큰 제목 + 시작 버튼 → 목차 → 01~08 단계(작은 혜택 문구 + 굵은 제목 + 설명) → 마지막 시작 버튼
//   (서비스 소개 페이지에서 흔한 "번호 단계 + 반복 CTA" 구성을 참고)
// 내용은 실제 기능·규칙 기준 — 예약 규칙은 docs/booking-rules.md, 체류 형태는 결정 28. 기능이 바뀌면 문구(guide.s.*)도 같이 고치기
const SECTIONS = [
  { key: 'about', to: '/hospitals' },
  { key: 'start', to: '/login' },
  { key: 'find', to: '/hospitals' },
  { key: 'chatbot', to: '/chatbot' },
  { key: 'booking', to: '/booking' },
  { key: 'before', to: '/mypage/bookings' },
  { key: 'after', to: '/aftercare' },
  { key: 'safety', to: '/legal/medical-law' },
] as const;

const num = (i: number) => String(i + 1).padStart(2, '0');

export function GuidePage() {
  const { t } = useTranslation();

  const ctas = (
    <div className="guide-ctas">
      <Link to="/hospitals" className="guide-cta">
        {t('guide.cta')} →
      </Link>
      <Link to="/chatbot" className="guide-cta is-secondary">
        {t('guide.cta2')} →
      </Link>
    </div>
  );

  return (
    <div className="mypage guide-page">
      <nav className="mp-breadcrumb" aria-label="breadcrumb">
        <Link to="/">{t('mypage.home')}</Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page" className="is-current">
          {t('nav.guide')}
        </span>
      </nav>

      <header className="guide-hero">
        <p className="guide-eyebrow">{t('guide.eyebrow')}</p>
        <h1>{t('guide.title')}</h1>
        <p className="guide-hero-sub">{t('guide.subtitle')}</p>
        {ctas}
      </header>

      {/* 목차: 누르면 그 단계로 이동 */}
      <nav className="guide-toc" aria-label={t('guide.toc')}>
        <ol>
          {SECTIONS.map((s, i) => (
            <li key={s.key}>
              <a href={`#guide-${s.key}`}>
                <span className="guide-num">{num(i)}</span>
                {t(`guide.s.${s.key}.title`)}
              </a>
            </li>
          ))}
        </ol>
      </nav>

      <ol className="guide-steps">
        {SECTIONS.map((s, i) => {
          const items = t(`guide.s.${s.key}.items`, { returnObjects: true }) as string[];
          return (
            <li key={s.key} id={`guide-${s.key}`} className={`mp-card guide-card ${s.key === 'safety' ? 'is-safety' : ''}`}>
              <span className="guide-step-no" aria-hidden="true">
                {num(i)}
              </span>
              <div className="guide-step-body">
                <p className="guide-eyebrow">{t(`guide.s.${s.key}.eyebrow`)}</p>
                <h2>{t(`guide.s.${s.key}.title`)}</h2>
                <ul>
                  {(Array.isArray(items) ? items : []).map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
                <Link to={s.to} className="guide-link">
                  {t(`guide.s.${s.key}.link`)} →
                </Link>
              </div>
            </li>
          );
        })}
      </ol>

      {/* 마지막에 다시 시작 버튼 */}
      <section className="guide-close">
        <h2>{t('guide.closeTitle')}</h2>
        {ctas}
      </section>

      <p className="guide-footnote">{t('guide.footnote')}</p>
      <LegalLinks />
    </div>
  );
}
