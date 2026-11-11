import { Fragment, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useChatText } from '../chatbot/ChatMessages';
import { kstDay, longDate, msgTime } from '../chatbot/time';
import { StaffIcon } from './icons';
import { BookingCard } from './BookingCard';
import type { ConsultThread } from './types';

// 한 병원과의 대화 전체 (날짜가 바뀌면 구분선)
export function ConsultMessages({ thread }: { thread: ConsultThread }) {
  const { t, i18n } = useTranslation();
  const text = useChatText();
  const end = useRef<HTMLDivElement>(null);
  const msgs = thread.messages;

  useEffect(() => {
    end.current?.scrollIntoView({ block: 'end' });
  }, [thread.hospitalId, msgs.length]);

  return (
    <div className="chat-log consult-log" role="log" aria-live="polite">
      {thread.sample && <p className="chat-sample-note">{t('consult.sampleNote')}</p>}
      {msgs.length === 0 && <p className="consult-empty">{t('consult.empty')}</p>}
      {msgs.map((m, i) => {
        const showDay = i === 0 || kstDay(m.at) !== kstDay(msgs[i - 1].at);
        return (
          <Fragment key={m.id}>
            {showDay && (
              <div className="chat-day">
                <span>{longDate(m.at, i18n.language)}</span>
              </div>
            )}
            {m.booking ? (
              <div className="consult-booking-row">
                <BookingCard booking={m.booking} sentAt={m.at} />
              </div>
            ) : (
              <div className={`chat-msg is-${m.from === 'staff' ? 'bot' : 'user'}`}>
                {m.from === 'staff' && (
                  <span className="chat-avatar consult-staff" aria-hidden="true">
                    <StaffIcon />
                  </span>
                )}
                <div className="chat-msg-body">
                  {m.from === 'staff' && <span className="consult-staff-name">{t('consult.staffLabel', { name: text(thread.name) })}</span>}
                  <div className="chat-bubble">
                    <p>{text(m.text ?? '')}</p>
                  </div>
                  <time className="chat-time" dateTime={m.at}>
                    {msgTime(m.at)}
                  </time>
                </div>
              </div>
            )}
          </Fragment>
        );
      })}
      <div ref={end} />
    </div>
  );
}
