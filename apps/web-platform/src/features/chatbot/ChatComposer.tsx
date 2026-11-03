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
}

// 화면 아래에 붙어 있는 빠른 메뉴 + 입력창 + 안내 문구
export function ChatComposer({ onSend, onTopic }: Props) {
  const { t } = useTranslation();
  const [text, setText] = useState('');
  const [quickOpen, setQuickOpen] = useState(true);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    onSend(text);
    setText('');
  };

  return (
    <div className="chat-composer">
      {quickOpen && (
        <div className="chat-quick" id="chat-quick">
          {QUICK.map(({ topic, Icon }) => (
            <button key={topic} type="button" onClick={() => onTopic(topic)}>
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
        />
        <button type="submit" className="chat-send" disabled={!text.trim()} aria-label={t('chat.send')}>
          <SendIcon />
        </button>
      </form>
      <p className="chat-disclaimer">{t('chat.disclaimer')}</p>
    </div>
  );
}
