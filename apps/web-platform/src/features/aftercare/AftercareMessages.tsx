import { Fragment, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocalized } from '../../lib/common';
import { kstDay, longDate, msgTime } from '../chatbot/time';
import { StaffIcon } from '../consult/icons';
import type { AftercareMessage, Attachment } from './types';

function AttachmentView({ a }: { a: Attachment }) {
  return a.kind === 'image' ? (
    <a href={a.url} target="_blank" rel="noopener noreferrer" className="aftercare-media">
      <img src={a.url} alt={a.name} />
    </a>
  ) : (
    <video className="aftercare-media" src={a.url} controls preload="metadata" aria-label={a.name} />
  );
}

// 한 방문(진료·시술)에 대한 의료진과의 대화
export function AftercareMessages({ messages, hospital, sample }: { messages: AftercareMessage[]; hospital: string; sample?: boolean }) {
  const { t, i18n } = useTranslation();
  const text = useLocalized();
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    end.current?.scrollIntoView({ block: 'end' });
  }, [messages.length, hospital]);

  return (
    <div className="chat-log consult-log" role="log" aria-live="polite">
      {sample && <p className="chat-sample-note">{t('aftercare.sampleNote')}</p>}
      {messages.length === 0 && <p className="consult-empty">{t('aftercare.empty')}</p>}
      {messages.map((m, i) => {
        const showDay = i === 0 || kstDay(m.at) !== kstDay(messages[i - 1].at);
        return (
          <Fragment key={m.id}>
            {showDay && (
              <div className="chat-day">
                <span>{longDate(m.at, i18n.language)}</span>
              </div>
            )}
            <div className={`chat-msg is-${m.from === 'doctor' ? 'bot' : 'user'}`}>
              {m.from === 'doctor' && (
                <span className="chat-avatar consult-staff" aria-hidden="true">
                  <StaffIcon />
                </span>
              )}
              <div className="chat-msg-body">
                {m.from === 'doctor' && <span className="consult-staff-name">{t('aftercare.doctorLabel', { name: hospital })}</span>}
                {m.attachments && (
                  <div className="aftercare-media-grid">
                    {m.attachments.map((a) => (
                      <AttachmentView key={a.url} a={a} />
                    ))}
                  </div>
                )}
                {m.text && (
                  <div className="chat-bubble">
                    <p>{text(m.text)}</p>
                  </div>
                )}
                <time className="chat-time" dateTime={m.at}>
                  {msgTime(m.at)}
                </time>
              </div>
            </div>
          </Fragment>
        );
      })}
      <div ref={end} />
    </div>
  );
}
