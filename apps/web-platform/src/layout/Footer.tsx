import { useTranslation } from 'react-i18next';

export function Footer() {
  const { t } = useTranslation();

  return (
    <footer className="site-footer">
      <p className="footer-notice">{t('footer.notice')}</p>
      <p>{t('footer.source')}</p>
      <p>{t('footer.emergency')}</p>
      <p className="footer-team">© 2026 MediDaegu · AXA, AX Native Bootcamp</p>
    </footer>
  );
}
