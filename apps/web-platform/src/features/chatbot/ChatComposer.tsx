import { useLayoutEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { CoinsIcon, HospitalIcon, PlusIcon, SendIcon, TranslateIcon } from './icons';
import type { Topic } from './types';

const QUICK: { topic: Topic; Icon: () => JSX.Element }[] = [
  { topic: 'hospital', Icon: HospitalIcon },
  { topic: 'price', Icon: CoinsIcon },
  { topic: 'interpret', Icon: TranslateIcon },
  // 대구 관광 빠른 메뉴는 뺌 (2026-11-26) — '관광'을 직접 물으면 답은 그대로 나옴
];

interface Props {
  onSend: (text: string) => void;
  onTopic: (topic: Topic) => void;
  busy: boolean; // 답을 기다리거나 지난 대화를 불러오는 중: 보내기만 막고 입력은 그대로 둔다
}

// 화면 아래에 붙어 있는 빠른 메뉴 + 입력창 + 안내 문구
export function ChatComposer({ onSend, onTopic, busy }: Props) {
  const { t } = useTranslation();
  const [text, setText] = useState('');
  const [quickOpen, setQuickOpen] = useState(true);
  const box = useRef<HTMLTextAreaElement>(null);

  // 입력한 줄 수만큼 높이를 늘린다 (최대 높이는 CSS max-height, 넘으면 스크롤)
  useLayoutEffect(() => {
    const el = box.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }, [text]);

  const send = () => {
    if (!text.trim() || busy) return;
    onSend(text.trim());
    setText('');
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    send();
  };

  // Enter = 보내기, Shift+Enter = 줄바꿈 (2026-11-26). 한글 등 조합 중의 Enter는 글자 확정이라 보내지 않는다
  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== 'Enter' || e.shiftKey || e.nativeEvent.isComposing || e.keyCode === 229) return;
    e.preventDefault();
    send();
  };

  return (
    <div className="chat-composer">
      {quickOpen && (
        <div className="chat-quick" id="chat-quick">
          {QUICK.map(({ topic, Icon }) => (
            <button key={topic} type="button" disabled={busy} onClick={() => onTopic(topic)}>
              <Icon />
              {t(`chat.topic.${topic}`)}
            </button>
          ))}
        </div>
      )}
      <form className="chat-input" onSubmit={submit}>
        <button
          type="button"
          className="chat-input-plus"
          aria-label={t('chat.quickMenu')}
          aria-expanded={quickOpen}
          aria-controls="chat-quick"
          onClick={() => setQuickOpen(!quickOpen)}
        >
          <PlusIcon />
        </button>
        <textarea
          ref={box}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={t('chat.placeholder')}
          aria-label={t('chat.placeholder')}
          enterKeyHint="send"
          autoComplete="off"
          maxLength={1000} // 서버 질문 길이 한도와 같음 (chat.api.validation)
        />
        <button type="submit" className="chat-send" disabled={!text.trim() || busy} aria-label={t('chat.send')}>
          <SendIcon />
        </button>
      </form>
      <p className="chat-disclaimer">{t('chat.disclaimer')}</p>
    </div>
  );
}
