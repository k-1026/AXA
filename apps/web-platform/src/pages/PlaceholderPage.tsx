import { useTranslation } from 'react-i18next';

// 아직 만들지 않은 메뉴용 임시 화면
export function PlaceholderPage({ titleKey }: { titleKey: string }) {
  const { t } = useTranslation();
  return (
    <section className="placeholder-page">
      <h1>{t(titleKey)}</h1>
      <p>{t('placeholder.comingSoon')}</p>
    </section>
  );
}
