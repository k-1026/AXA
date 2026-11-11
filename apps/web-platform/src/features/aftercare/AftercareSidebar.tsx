import { useTranslation } from 'react-i18next';
import { CloseIcon } from '../chatbot/icons';
import { useChatText } from '../chatbot/ChatMessages';
import { InfoIcon } from '../mypage/icons';
import { HospitalThumb } from '../consult/HospitalThumb';
import { bookingDateFull } from '../consult/format';
import type { useAftercare } from './useAftercare';

type Visit = ReturnType<typeof useAftercare>['visits'][number];

interface Props {
  visits: Visit[];
  activeId: string | undefined;
  demo: boolean;
  onSelect: (id: string) => void;
  onClose: () => void;
}

// 왼쪽 사후 관리 내역: 방문을 마친 예약 1건 = 1줄
export function AftercareSidebar({ visits, activeId, demo, onSelect, onClose }: Props) {
  const { t, i18n } = useTranslation();
  const text = useChatText();

  return (
    <aside className="chat-sidebar consult-sidebar" aria-label={t('aftercare.list')}>
      <div className="chat-sidebar-top aftercare-top">
        <h2 className="chat-history-title">{t('aftercare.list')}</h2>
        <button type="button" className="chat-icon-button chat-drawer-close" onClick={onClose} aria-label={t('consult.closeMenu')}>
          <CloseIcon />
        </button>
      </div>
      <p className="aftercare-hint">{t('aftercare.listHint')}</p>
      <div className="chat-history">
        {visits.length === 0 && <p className="chat-history-empty">{t('aftercare.none')}</p>}
        <ul className="consult-list">
          {visits.map((v) => (
            <li key={v.id} className={v.id === activeId ? 'is-active' : undefined}>
              <button type="button" className="consult-item" aria-current={v.id === activeId ? 'true' : undefined} onClick={() => onSelect(v.id)}>
                <HospitalThumb photo={v.thread.photo} />
                <span className="consult-item-text">
                  <span className="consult-item-row">
                    <strong>{text(v.thread.name)}</strong>
                    {v.unread > 0 && (
                      <span className="consult-badge" aria-label={t('consult.unread', { count: v.unread })}>
                        {v.unread}
                      </span>
                    )}
                  </span>
                  <span className="consult-preview">{v.booking.treatment ? text(v.booking.treatment) : t(`dept.${v.thread.dept}`)}</span>
                  <span className="consult-preview">{t('aftercare.visitedOn', { date: bookingDateFull(v.booking.date, v.booking.time, i18n.language) })}</span>
                </span>
              </button>
            </li>
          ))}
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
