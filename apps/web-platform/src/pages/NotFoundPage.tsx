import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

// 없는 주소 (예: /hospitals/abc/def, /foo). 빈 화면 대신 안내와 메인 링크
export function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <section className="placeholder-page">
      <h1>{t('notFoundPage.title')}</h1>
      <p>{t('notFoundPage.body')}</p>
      <p>
        <Link to="/">{t('notFoundPage.home')}</Link>
      </p>
    </section>
  );
}
