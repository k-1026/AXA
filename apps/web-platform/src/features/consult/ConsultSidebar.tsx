import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { CloseIcon, SearchIcon } from '../chatbot/icons';
import { useLocalized } from '../../lib/common';
import { CalendarIcon, InfoIcon } from '../mypage/icons';
import { HospitalThumb } from './HospitalThumb';
import { shortDate } from './format';
import type { ConsultThread } from './types';

interface Props {
  activeId: string | undefined;
  search: (q: string) => ConsultThread[];
  demo: boolean;
  onSelect: (id: string) => void;
  onClose: () => void; // 모바일 서랍 닫기
}

// 왼쪽 병원별 상담 목록. 병원 1곳 = 1줄 (날짜와 상관없이 한 상담에 쌓임)
export function ConsultSidebar({ activeId, search, demo, onSelect, onClose }: Props) {
  const { t, i18n } = useTranslation();
  const text = useLocalized();
  const [query, setQuery] = useState('');
  const items = search(query);

  const preview = (th: ConsultThread) => {
    const last = th.messages[th.messages.length - 1];
    if (!last) return t('consult.newThread');
    if (last.booking) return last.booking.status === 'pending' ? t('consult.bookingSent') : t(`consult.status.${last.booking.status}`);
    return text(last.text ?? '');
  };

  return (
    <aside className="chat-sidebar consult-sidebar" aria-label={t('consult.threads')}>
      <div className="chat-sidebar-top">
        <Link to="/mypage/bookings" className="chat-new">
          <CalendarIcon />
          {t('consult.manageBookings')}
        </Link>
        <button type="button" className="chat-icon-button chat-drawer-close" onClick={onClose} aria-label={t('consult.closeMenu')}>
          <CloseIcon />
        </button>
      </div>


      <label className="chat-search">
        <SearchIcon />
        <span className="visually-hidden">{t('consult.search')}</span>
        <input type="search" value={query} placeholder={t('consult.search')} onChange={(e) => setQuery(e.target.value)} />
      </label>
      <h2 className="chat-history-title">{t('consult.threads')}</h2>
      <div className="chat-history">
        {items.length === 0 && <p className="chat-history-empty">{t(query ? 'consult.noResults' : 'consult.noThreads')}</p>}
        <ul className="consult-list">
          {items.map((th) => {
            const last = th.messages[th.messages.length - 1];
            return (
              <li key={th.hospitalId} className={th.hospitalId === activeId ? 'is-active' : undefined}>
                <button
                  type="button"
                  className="consult-item"
                  aria-current={th.hospitalId === activeId ? 'true' : undefined}
                  onClick={() => onSelect(th.hospitalId)}
                >
                  <HospitalThumb photo={th.photo} />
                  <span className="consult-item-text">
                    <span className="consult-item-row">
                      <strong>{text(th.name)}</strong>
                      {last && <time dateTime={last.at}>{shortDate(last.at, i18n.language)}</time>}
                    </span>
                    <span className="consult-item-row">
                      <span className="consult-preview">{preview(th)}</span>
                      {th.unread > 0 && (
                        <span className="consult-badge" aria-label={t('consult.unread', { count: th.unread })}>
                          {th.unread}
                        </span>
                      )}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      {demo && (
        <div className="chat-sidebar-foot">
          <p>
            <InfoIcon />
            {t('consult.sampleHospitals')}
          </p>
        </div>
      )}
    </aside>
  );
}
