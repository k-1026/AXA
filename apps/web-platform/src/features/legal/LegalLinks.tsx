import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LEGAL_DOCUMENTS, pickText } from './documents';

// 개인정보 처리방침 | 이용약관 | AI 서비스 안내 | 의료 관련 법령 안내
export function LegalLinks() {
  const { t, i18n } = useTranslation();

  return (
    <nav className="legal-links" aria-label={t('legal.label')}>
      <ul>
        {LEGAL_DOCUMENTS.map((d) => (
          <li key={d.slug}>
            <NavLink to={`/legal/${d.slug}`}>{pickText(d.linkLabel ?? d.title, i18n.language)}</NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
