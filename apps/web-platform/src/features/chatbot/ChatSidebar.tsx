import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { MoreMenu } from './MoreMenu';
import { BotIcon, CloseIcon, GearIcon, InfoIcon, PlusIcon, SearchIcon } from './icons';
import { dayGroup, dotDate, listTime } from './time';
import type { Conversation } from './types';
import { lastActivity, type ChatMode } from './useConversations';

interface Props {
  mode: ChatMode;
  activeId: string | undefined;
  search: (q: string) => Conversation[];
  onNew: () => void;
  onSelect: (id: string) => void;
  onDelete: (c: Conversation) => void;
  onClose: () => void; // 모바일 서랍 닫기
}

const GROUPS = ['today', 'yesterday', 'earlier'] as const;

// 왼쪽 대화 목록. PC에서는 고정, 모바일에서는 서랍
export function ChatSidebar({ mode, activeId, search, onNew, onSelect, onDelete, onClose }: Props) {
  const { t, i18n } = useTranslation();
  const [query, setQuery] = useState('');
  const items = search(query);
  const now = new Date();

  return (
    <aside className="chat-sidebar" aria-label={t('chat.history')}>
      <div className="chat-sidebar-top">
        <button type="button" className="chat-new" onClick={onNew}>
          <PlusIcon />
          {t('chat.new')}
        </button>
        <button type="button" className="chat-icon-button chat-drawer-close" onClick={onClose} aria-label={t('chat.closeMenu')}>
          <CloseIcon />
        </button>
      </div>

      <label className="chat-search">
        <SearchIcon />
        <span className="visually-hidden">{t('chat.search')}</span>
        <input type="search" value={query} placeholder={t('chat.search')} onChange={(e) => setQuery(e.target.value)} />
      </label>

      <h2 className="chat-history-title">{t('chat.history')}</h2>
      <div className="chat-history">
        {items.length === 0 && <p className="chat-history-empty">{t(query ? 'chat.noResults' : 'chat.noHistory')}</p>}
        {GROUPS.map((g) => {
          const group = items.filter((c) => dayGroup(lastActivity(c), now) === g); // 목록 순서(마지막 메시지)와 같은 기준
          if (!group.length) return null;
          return (
            <section key={g} className="chat-history-group">
              <h3>{t(`chat.group.${g}`)}</h3>
              <ul>
                {group.map((c) => (
                  <li key={c.id} className={c.id === activeId ? 'is-active' : undefined}>
                    <button
                      type="button"
                      className="chat-history-item"
                      aria-current={c.id === activeId ? 'true' : undefined}
                      onClick={() => onSelect(c.id)}
                    >
                      <span className="chat-history-icon">
                        <BotIcon />
                      </span>
                      <span className="chat-history-text">
                        <strong>
                          {dotDate(c.createdAt)}
                          {c.sample && <span className="chat-sample-tag">{t('chat.sample')}</span>}
                        </strong>
                        <span>
                          {listTime(lastActivity(c), i18n.language)} · {t(c.topic ? `chat.summary.${c.topic}` : 'chat.summary.none')}
                        </span>
                      </span>
                    </button>
                    <MoreMenu
                      label={t('chat.more', { title: dotDate(c.createdAt) })}
                      items={[{ label: t('chat.delete'), danger: true, onSelect: () => onDelete(c) }]}
                    />
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>

      <div className="chat-sidebar-foot">
        <p>
          <InfoIcon />
          {t(`chat.saveNote.${mode}`)}
        </p>
        <Link to={mode === 'guest' ? '/login' : '/mypage'} state={{ from: '/chatbot' }} className="chat-settings">
          <GearIcon />
          {t(mode === 'guest' ? 'chat.login' : 'chat.settings')}
        </Link>
      </div>
    </aside>
  );
}
