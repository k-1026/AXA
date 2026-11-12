import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { CoinsIcon, HospitalIcon, PinIcon, PlusIcon, SendIcon, TranslateIcon } from './icons';
import type { Topic } from './types';

const QUICK: { topic: Topic; Icon: () => JSX.Element }[] = [
  { topic: 'hospital', Icon: HospitalIcon },
  { topic: 'price', Icon: CoinsIcon },
  { topic: 'interpret', Icon: TranslateIcon },
  { topic: 'tour', Icon: PinIcon },
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

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim() || busy) return;
    onSend(text);
    setText('');
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
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
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
