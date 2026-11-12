import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { onAccountReset, type AccountKey } from '../../components/account';
import { ApiError } from '../../components/api';
import { useAuth } from '../../components/auth';
import { askChatbot, chatLang, deleteChatSession, getChatSession, listChatSessions } from './chatApi';
import { GREETING, SAMPLE_CONVERSATIONS } from './sampleConversations';
import { replyToChip, replyToText, type BotReply } from './replies';
import { dotDate } from './time';
import type { ChatMessage, ChipAction, ChatText, Conversation } from './types';
import { useChatText } from './ChatMessages';

// 대화 저장 방식 (마이페이지와 같은 구조). 챗봇은 로그인한 사람만 쓴다 (main.tsx RequireLogin, plan-step7 결정 4)
// - demo: 데모 계정. 예시 대화로 시작, 바꾼 내용은 메모리에만 (탭을 닫으면 사라짐)
// - member: 실제 회원. 질문은 POST /chatbot/ask(AI)로 보내고 서버가 대화를 저장 (7d). 화면 목록은 아직 메모리
//   화면을 열면 서버의 지난 대화 목록을 불러오고(7e), 대화를 고르면 그때 메시지를 불러온다. 카드는 저장하지 않아 글만 보임
// 메모리는 계정별(account 키)로 나누고, 로그아웃·탈퇴하면 모두 지운다 (같은 탭의 다음 사용자에게 보이지 않게)
export type ChatMode = 'demo' | 'member';

const memory = new Map<AccountKey, Conversation[]>();
onAccountReset(() => memory.clear());

// 서버 에러 코드 → 화면 문구 키 (chat.api.*)
const API_ERRORS: Record<string, string> = {
  network: 'network',
  rate_limited: 'rateLimited', // detail.limit이 sessions면 tooManySessions (askServer)
  'chatbot.unavailable': 'unavailable',
  'auth.required': 'login',
  not_found: 'notFound',
  validation: 'validation',
};

// 인사말만 있는 대화는 아직 시작하지 않은 대화로 본다
const isBlank = (c: Conversation) => !c.remote && c.messages.every((m) => m.role === 'bot');

// 목록에 시작 전 대화가 하나는 있게 해서 화면을 열면 바로 입력할 수 있게 한다
const withBlank = (list: Conversation[]) => (list.some(isBlank) ? list : [newConversation(), ...list]);

function load(key: AccountKey, mode: ChatMode): Conversation[] {
  const list = withBlank(memory.get(key) ?? (mode === 'demo' ? SAMPLE_CONVERSATIONS : []));
  memory.set(key, list);
  return list;
}

// 회원 대화는 질문할 때 서버가 저장하므로 여기서는 화면 목록(메모리)만 갱신
function save(key: AccountKey, list: Conversation[]) {
  memory.set(key, list);
}

const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
const now = () => new Date().toISOString();

function newConversation(): Conversation {
  const at = now();
  return { id: uid(), createdAt: at, messages: [{ id: uid(), role: 'bot', text: GREETING, at }] };
}

const textOf = (x: ChatText) => (typeof x === 'string' ? x : `${x.ko} ${x.en}`);

/** 마지막 활동 시각: 화면에 있는 마지막 메시지, 아직 안 불러온 서버 대화는 서버의 last_message_at */
export function lastActivity(c: Conversation): string {
  return c.messages[c.messages.length - 1]?.at ?? c.lastMessageAt ?? c.createdAt;
}

export function useConversations() {
  const { t, i18n } = useTranslation();
  const { user, account, token } = useAuth();
  const mode: ChatMode = user?.demo ? 'demo' : 'member';

  const [list, setList] = useState<Conversation[]>(() => load(account, mode));
  const [activeId, setActiveId] = useState<string | null>(null);
  const accountRef = useRef(account);
  accountRef.current = account;

  // 로그인·로그아웃하면 그 계정의 대화로 바꿔 끼운다
  useEffect(() => {
    setList(load(account, mode));
    setActiveId(null);
  }, [account, mode]);

  // owner: 요청을 보낸 때의 계정. 응답이 오기 전에 로그아웃·계정 전환이 됐으면 그 결과는 버린다
  // (예전 계정 목록이 새 계정 화면·메모리에 섞이지 않게)
  const update = useCallback((fn: (prev: Conversation[]) => Conversation[], owner: AccountKey = accountRef.current) => {
    if (owner !== accountRef.current) return;
    setList((prev) => {
      const next = fn(prev);
      save(owner, next);
      return next;
    });
  }, []);

  const loading = useRef(new Set<string>()); // 메시지를 불러오는 중인 대화 (같은 요청을 두 번 보내지 않게)
  const deleted = useRef(new Set<string>()); // 첫 답을 기다리는 중에 지운 대화 (답이 오면 서버 대화도 지움)
  const [error, setError] = useState<string | null>(null); // 대화 삭제 실패 등 화면 위에 보여 줄 안내

  // 회원: 서버의 지난 대화 목록 (이미 화면에 있는 대화는 그대로)
  useEffect(() => {
    if (mode !== 'member' || !token) return;
    let stop = false;
    const owner = accountRef.current;
    listChatSessions(token)
      .then((rows) => {
        if (stop) return;
        update((prev) => {
          const known = new Set(prev.map((c) => c.serverId).filter(Boolean));
          const fromServer: Conversation[] = rows
            .filter((r) => !known.has(r.id))
            .map((r) => ({ id: r.id, serverId: r.id, createdAt: r.created_at, lastMessageAt: r.last_message_at, messages: [], remote: true }));
          return fromServer.length ? [...prev, ...fromServer] : prev;
        }, owner);
      })
      .catch(() => {}); // 목록을 못 받아도 새 대화는 할 수 있게
    return () => {
      stop = true;
    };
  }, [mode, token, update]);

  // 목록은 마지막 메시지가 최근인 순 (서버 목록과 같은 기준)
  // (예시는 +09:00, 새 대화는 UTC 형식이라 문자열이 아닌 시각으로 비교)
  const sorted = useMemo(() => [...list].sort((a, b) => Date.parse(lastActivity(b)) - Date.parse(lastActivity(a))), [list]);

  // 고른 대화가 없으면 시작 전 대화를 보여준다
  const active = sorted.find((c) => c.id === activeId) ?? sorted.find(isBlank) ?? sorted[0] ?? null;

  // 회원: 서버에서만 받은 대화를 열면 메시지를 불러온다 (첫 인사 + 저장된 글)
  // 불러오는 동안은 입력을 막아(busy) 새 질문이 불러온 글에 덮이지 않게 한다
  useEffect(() => {
    if (!active?.remote || active.loadFailed || !active.serverId || !token || loading.current.has(active.id)) return;
    const { id, serverId, createdAt } = active;
    const owner = accountRef.current;
    loading.current.add(id);
    getChatSession(token, serverId)
      .then((d) =>
        update(
          (prev) =>
            prev.map((c) =>
              c.id !== id
                ? c
                : {
                    ...c,
                    remote: false,
                    messages: [
                      { id: uid(), role: 'bot', text: GREETING, at: createdAt },
                      ...d.messages.map((m): ChatMessage => ({
                        id: uid(),
                        role: m.role === 'user' ? 'user' : 'bot',
                        text: m.content,
                        at: m.created_at,
                        // 응급 안내·거절 문구(refused)는 고정 문구라 "AI 생성" 표시를 하지 않는다
                        ...(m.role === 'assistant' ? { ai: !m.refused } : {}),
                      })),
                    ],
                  },
            ),
          owner,
        ),
      )
      .catch((e) => {
        // 서버에서 지워진 대화(30일 정리 등)만 목록에서 뺀다. 그 밖의 오류는 남겨 두고 다시 시도할 수 있게
        if (e instanceof ApiError && e.code === 'not_found') update((prev) => withBlank(prev.filter((c) => c.id !== id)), owner);
        else update((prev) => prev.map((c) => (c.id === id ? { ...c, loadFailed: true } : c)), owner);
      })
      .finally(() => loading.current.delete(id));
  }, [active, token, update]);

  const retryLoad = (id: string) => update((prev) => prev.map((c) => (c.id === id ? { ...c, loadFailed: false } : c)));

  const startNew = () => {
    const blank = sorted.find(isBlank);
    if (blank) return setActiveId(blank.id);
    const c = newConversation();
    update((prev) => [c, ...prev]);
    setActiveId(c.id);
  };

  const remove = (id: string) => {
    const target = list.find((c) => c.id === id);
    if (!target) return;
    const owner = accountRef.current;
    if (target.messages.some((m) => m.pending)) deleted.current.add(id); // 답이 오면 그때 생긴 서버 대화도 지움 (askServer)
    if (mode === 'member' && token && target.serverId) {
      deleteChatSession(token, target.serverId).catch((e) => {
        if (e instanceof ApiError && e.code === 'not_found') return; // 이미 서버에 없음
        // 지우지 못했으면 목록에 되돌리고 알려 준다
        update((prev) => (prev.some((c) => c.id === id) ? prev : [target, ...prev]), owner);
        setError(t('chat.deleteFailed'));
      });
    }
    update((prev) => withBlank(prev.filter((c) => c.id !== id)));
    if (id === active?.id) setActiveId(null);
  };

  const push = (id: string, userText: ChatText, reply: BotReply | null) => {
    const at = now();
    setActiveId(id); // 보내는 순간 시작 전 대화가 아니게 되므로 선택을 고정
    update((prev) =>
      prev.map((c) => {
        if (c.id !== id) return c;
        const msgs: ChatMessage[] = [...c.messages, { id: uid(), role: 'user', text: userText, at }];
        if (reply) msgs.push({ id: uid(), role: 'bot', text: reply.text, chips: reply.chips, at });
        return { ...c, messages: msgs, topic: c.topic ?? reply?.topic, dept: reply?.dept ?? c.dept };
      }),
    );
  };

  // 회원: 질문을 바로 보여 주고, 답이 올 때까지 "답을 준비하는 중" 말풍선을 둔다
  const askServer = async (conv: Conversation, userText: string) => {
    if (!token) return;
    const owner = accountRef.current;
    const at = now();
    const waitId = uid();
    setActiveId(conv.id);
    update((prev) =>
      prev.map((c) =>
        c.id !== conv.id
          ? c
          : { ...c, messages: [...c.messages, { id: uid(), role: 'user', text: userText, at }, { id: waitId, role: 'bot', text: '', at, pending: true }] },
      ),
    );
    let serverId = conv.serverId;
    let patch: Partial<ChatMessage>;
    try {
      const r = await askChatbot(token, conv.serverId, userText, chatLang(i18n.language));
      serverId = r.session_id;
      patch = { text: r.text, cards: r.cards, ai: r.ai_generated, medicalNotice: r.medical_notice, at: now() };
    } catch (e) {
      const code = e instanceof ApiError ? e.code : 'unknown';
      if (code === 'not_found') serverId = undefined; // 서버에서 지워진 대화 → 다음 질문은 새 대화로
      // 429는 한도 종류(detail.limit)에 따라 문구가 다르다: sessions = 저장된 대화 수 한도
      const sessionsFull = code === 'rate_limited' && e instanceof ApiError && e.detail.limit === 'sessions';
      patch = { text: t(`chat.api.${sessionsFull ? 'tooManySessions' : API_ERRORS[code] ?? 'error'}`), failed: true };
    }
    // 답을 기다리는 동안 사용자가 이 대화를 지웠다면, 그 사이 서버에 새로 생긴 대화도 지운다
    if (deleted.current.has(conv.id)) {
      deleted.current.delete(conv.id);
      if (serverId && serverId !== conv.serverId) deleteChatSession(token, serverId).catch(() => setError(t('chat.deleteFailed')));
      return;
    }
    update(
      (prev) =>
        prev.map((c) =>
          c.id !== conv.id ? c : { ...c, serverId, messages: c.messages.map((m) => (m.id === waitId ? { ...m, ...patch, pending: false } : m)) },
        ),
      owner,
    );
  };

  // 답을 기다리는 중이거나, 지난 대화의 메시지를 아직 불러오지 못했으면 입력을 막는다
  const busy = !!active && (active.messages.some((m) => m.pending) || !!active.remote);
  const shown = useChatText();

  const send = (text: string) => {
    if (!active || !text.trim() || busy) return;
    if (mode === 'member') return void askServer(active, text.trim());
    push(active.id, text.trim(), replyToText(t, text));
  };

  const choose = (label: ChatText, action: ChipAction) => {
    if (!active || busy) return;
    if (mode === 'member') return void askServer(active, shown(label)); // 버튼 문구를 질문으로
    push(active.id, label, replyToChip(t, action, active));
  };

  const search = (q: string) => {
    const s = q.trim().toLowerCase();
    if (!s) return sorted;
    return sorted.filter(
      (c) =>
        dotDate(c.createdAt).includes(s) ||
        (c.topic && t(`chat.summary.${c.topic}`).toLowerCase().includes(s)) ||
        // 모든 대화에 있는 인사말은 빼고 찾는다
        c.messages.some((m) => m.text !== GREETING && textOf(m.text).toLowerCase().includes(s)),
    );
  };

  return {
    mode,
    busy,
    conversations: sorted,
    active,
    select: setActiveId,
    startNew,
    remove,
    retryLoad,
    send,
    choose,
    search,
    error,
    dismissError: () => setError(null),
  };
}
