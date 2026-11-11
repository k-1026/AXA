import { useTranslation } from 'react-i18next';

const CONTACT_EMAIL = 'indeok419@naver.com';

export function Footer() {
  const { t } = useTranslation();

  return (
    <footer className="site-footer">
      <div className="footer-main">
        <section className="footer-about">
          <h2 className="footer-team-name">Team AXA</h2>
          <p>{t('footer.about')}</p>
          <p>{t('footer.service')}</p>
        </section>
        <section className="footer-info">
          <p className="footer-contact">
            {t('footer.contact')}: <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
          </p>
          <p className="footer-notice">{t('footer.disclaimer')}</p>
          <p>{t('footer.source')}</p>
          <p>{t('footer.emergency')}</p>
        </section>
      </div>
      <p className="footer-team">
        © 2026 MediDaegu · Team AXA
        <br />
        AX Native Bootcamp
      </p>
    </footer>
  );
}
