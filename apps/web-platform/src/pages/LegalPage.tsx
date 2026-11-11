import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { findLegalDocument, pickText } from '../features/legal/documents';
import { LegalLinks } from '../features/legal/LegalLinks';
import type { Text } from '../features/legal/types';

// 약관·정책 문서
export function LegalPage() {
  const { slug } = useParams();
  const { t, i18n } = useTranslation();
  const tx = (x: Text) => pickText(x, i18n.language);
  const doc = findLegalDocument(slug);

  if (!doc) {
    return (
      <section className="placeholder-page">
        <h1>{t('legal.notFound')}</h1>
        <Link to="/mypage">{t('legal.back')}</Link>
      </section>
    );
  }

  const koreanOnly = i18n.language !== 'ko' && !doc.title.en;
  // 번역이 없어 한국어 원문을 보여줄 때는 한국어 글꼴·줄바꿈으로
  const docLang = koreanOnly ? 'ko' : undefined;

  return (
    <div className="legal-page">
      <Link to="/mypage" className="back-link">
        ← {t('legal.back')}
      </Link>
      <article className="legal-doc">
        <h1 lang={docLang}>{tx(doc.title)}</h1>
        <p className="legal-meta">{t('legal.updated', { date: doc.updated })}</p>
        <p className="legal-draft">{t('legal.draft')}</p>
        {koreanOnly && <p className="legal-draft">{t('legal.koreanOnly')}</p>}
        {doc.sections.map((s, i) => {
          const List = s.list?.ordered ? 'ol' : 'ul';
          return (
            <section key={i} lang={docLang}>
              {s.heading && <h2>{tx(s.heading)}</h2>}
              {s.subheading && <h3>{tx(s.subheading)}</h3>}
              {s.body?.map((p) => <p key={p.ko}>{tx(p)}</p>)}
              {s.list && (
                <List className="legal-list">
                  {s.list.items.map((item) => (
                    <li key={item.ko}>{tx(item)}</li>
                  ))}
                </List>
              )}
              {s.table && (
                <div className="legal-table-wrap">
                  <table className={s.table.head.length > 3 ? 'legal-table wide' : 'legal-table'}>
                    <thead>
                      <tr>
                        {s.table.head.map((h) => (
                          <th key={h.ko} scope="col">
                            {tx(h)}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {s.table.rows.map((row) => (
                        <tr key={row[0].ko}>
                          {row.map((cell) => (
                            <td key={cell.ko}>{tx(cell)}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {s.links && (
                <ul className="legal-sources">
                  {s.links.map((l) => (
                    <li key={l.url}>
                      {l.url.startsWith('/') ? (
                        <Link to={l.url}>{tx(l.label)}</Link>
                      ) : (
                        <a href={l.url} target="_blank" rel="noreferrer">
                          {tx(l.label)}
                        </a>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          );
        })}
      </article>
      <LegalLinks />
    </div>
  );
}
