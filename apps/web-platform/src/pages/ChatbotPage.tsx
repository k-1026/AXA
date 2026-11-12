import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ChatSidebar } from '../features/chatbot/ChatSidebar';
import { ChatMessages } from '../features/chatbot/ChatMessages';
import { ChatComposer } from '../features/chatbot/ChatComposer';
import { MoreMenu } from '../features/chatbot/MoreMenu';
import { BotIcon, MenuIcon } from '../features/chatbot/icons';
import { useConversations } from '../features/chatbot/useConversations';
import { useVisualViewport } from '../features/chatbot/useVisualViewport';
import { dotDate } from '../features/chatbot/time';
import type { Conversation } from '../features/chatbot/types';

// 챗봇 화면. 사이트 헤더·메뉴는 공통 레이아웃 그대로 두고, 대화 기록은 이 영역 안에 따로 둔다
// 모바일 대화 기록 서랍도 이 영역 안에서만 열려 사이트 메뉴를 가리지 않는다. 광고 없음 (docs/compliance.md)
export function ChatbotPage() {
  const { t } = useTranslation();
  const chat = useConversations();
  const [drawer, setDrawer] = useState(false);
  const [deleting, setDeleting] = useState<Conversation | null>(null);
  useVisualViewport();

  // 모바일 서랍: Esc로 닫기
  useEffect(() => {
    if (!drawer) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setDrawer(false);
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [drawer]);

  // 브라우저 확인창(window.confirm)은 앱 내 브라우저 등에서 막힐 수 있어 화면 안에서 확인
  const remove = (c: Conversation) => {
    setDeleting(c);
    setDrawer(false); // 모바일 서랍에 가려지지 않게
  };

  const active = chat.active;

  return (
    <div className={drawer ? 'chat-app is-drawer-open' : 'chat-app'}>
      <ChatSidebar
        mode={chat.mode}
        activeId={active?.id}
        search={chat.search}
        onNew={() => {
          chat.startNew();
          setDrawer(false);
        }}
        onSelect={(id) => {
          chat.select(id);
          setDrawer(false);
        }}
        onDelete={remove}
        onClose={() => setDrawer(false)}
      />
      <div className="chat-scrim" onClick={() => setDrawer(false)} aria-hidden="true" />

      <section className="chat-main" aria-labelledby="chat-title">
        <div className="chat-title">
          <button
            type="button"
            className="chat-icon-button chat-menu-button"
            onClick={() => setDrawer(true)}
            aria-label={t('chat.openMenu')}
            aria-expanded={drawer}
          >
            <MenuIcon />
          </button>
          <span className="chat-title-icon" aria-hidden="true">
            <BotIcon />
          </span>
          <div>
            <h1 id="chat-title">{t('chat.title')}</h1>
            <p>{t('chat.subtitle')}</p>
          </div>
          {active && (
            <>
              <span className="chat-date-chip">{dotDate(active.createdAt)}</span>
              <MoreMenu
                label={t('chat.more', { title: dotDate(active.createdAt) })}
                items={[{ label: t('chat.delete'), danger: true, onSelect: () => remove(active) }]}
              />
            </>
          )}
        </div>

        {deleting && (
          <div className="chat-delete-confirm" role="alert">
            <p>{t('chat.confirmDelete', { title: dotDate(deleting.createdAt) })}</p>
            <button type="button" onClick={() => setDeleting(null)}>
              {t('chat.cancel')}
            </button>
            <button
              type="button"
              className="is-danger"
              onClick={() => {
                chat.remove(deleting.id);
                setDeleting(null);
              }}
            >
              {t('chat.delete')}
            </button>
          </div>
        )}

        {chat.error && (
          <div className="chat-delete-confirm" role="alert">
            <p>{chat.error}</p>
            <button type="button" onClick={chat.dismissError}>
              {t('chat.dismiss')}
            </button>
          </div>
        )}

        {active && (
          <ChatMessages conversation={active} onChip={(c) => chat.choose(c.label, c.action)} onRetry={() => chat.retryLoad(active.id)} />
        )}

        <ChatComposer
          busy={chat.busy}
          onSend={chat.send}
          onTopic={(topic) => chat.choose(t(`chat.topic.${topic}`), { kind: 'topic', topic })}
        />
      </section>
    </div>
  );
}
