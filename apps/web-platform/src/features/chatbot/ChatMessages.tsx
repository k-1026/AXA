import { Fragment, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { BotIcon, CopyIcon, ThumbIcon } from './icons';
import { AnswerText, ChatCards } from './ChatCards';
import { kstDay, longDate, msgTime } from './time';
import type { ChatMessage, ChatText, Chip, Conversation } from './types';

interface Props {
  conversation: Conversation;
  onChip: (chip: Chip) => void;
}

// 한국어 화면은 한국어, 그 밖의 언어는 영어 (예시 데이터). 사용자가 입력한 대화는 그대로
export const useChatText = () => {
  const { i18n } = useTranslation();
  return (x: ChatText) => (typeof x === 'string' ? x : i18n.language === 'ko' ? x.ko : x.en);
};

function BotActions({ text }: { text: string }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const [liked, setLiked] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // 복사 권한이 없으면 무시
    }
  };

  return (
    <div className="chat-msg-actions">
      <button type="button" className="chat-icon-button" onClick={copy} aria-label={t('chat.copy')}>
        <CopyIcon />
      </button>
      <button type="button" className="chat-icon-button" aria-pressed={liked} onClick={() => setLiked(!liked)} aria-label={t('chat.like')}>
        <ThumbIcon />
      </button>
      <span className="chat-copied" role="status">
        {copied ? t('chat.copied') : ''}
      </span>
    </div>
  );
}

export function ChatMessages({ conversation, onChip }: Props) {
  const { t, i18n } = useTranslation();
  const text = useChatText();
  const navigate = useNavigate();
  const end = useRef<HTMLDivElement>(null);
  const msgs = conversation.messages;

  // 새 메시지가 오면 맨 아래로
  useEffect(() => {
    end.current?.scrollIntoView({ block: 'end' });
  }, [conversation.id, msgs.length, msgs[msgs.length - 1]?.pending]); // AI 답이 "준비 중"을 대신할 때도

  const isLastBot = (m: ChatMessage) => m === msgs[msgs.length - 1];

  return (
    <div className="chat-log" role="log" aria-live="polite">
      {conversation.sample && <p className="chat-sample-note">{t('chat.sampleNote')}</p>}
      {msgs.map((m, i) => {
        const showDay = i === 0 || kstDay(m.at) !== kstDay(msgs[i - 1].at);
        return (
          <Fragment key={m.id}>
            {showDay && (
              <div className="chat-day">
                <span>{longDate(m.at, i18n.language)}</span>
              </div>
            )}
            <div className={`chat-msg is-${m.role}`}>
              {m.role === 'bot' && (
                <span className="chat-avatar" aria-hidden="true">
                  <BotIcon />
                </span>
              )}
              <div className="chat-msg-body">
                <div className={m.failed ? 'chat-bubble is-failed' : 'chat-bubble'}>
                  {m.pending ? (
                    <p className="chat-pending">{t('chat.api.thinking')}</p>
                  ) : m.ai !== undefined && m.role === 'bot' ? (
                    <AnswerText text={text(m.text)} />
                  ) : (
                    <p>{text(m.text)}</p>
                  )}
                  {m.cards && <ChatCards cards={m.cards} />}
                  {(m.ai || m.medicalNotice) && (
                    <p className="chat-ai-note">
                      {m.ai && <span className="chat-ai-badge">{t('chat.api.aiGenerated')}</span>}
                      {m.medicalNotice && <span>{t('chat.api.medicalNotice')}</span>}
                    </p>
                  )}
                  {m.chips && (
                    <div className="chat-chips">
                      {m.chips.map((c) => (
                        <button
                          key={text(c.label)}
                          type="button"
                          // 지난 질문의 버튼은 링크만 계속 쓸 수 있다
                          disabled={c.action.kind !== 'link' && !isLastBot(m)}
                          onClick={() => (c.action.kind === 'link' ? navigate(c.action.to) : onChip(c))}
                        >
                          {text(c.label)}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <time className="chat-time" dateTime={m.at}>
                  {msgTime(m.at)}
                </time>
                {m.role === 'bot' && i > 0 && !m.pending && <BotActions text={text(m.text)} />}
              </div>
            </div>
          </Fragment>
        );
      })}
      <div ref={end} />
    </div>
  );
}
