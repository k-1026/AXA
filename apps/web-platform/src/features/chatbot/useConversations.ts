import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ApiError } from '../../components/api';
import { useAuth } from '../../components/auth';
import { askChatbot, chatLang, deleteChatSession, getChatSession, listChatSessions } from './chatApi';
import { GREETING, SAMPLE_CONVERSATIONS } from './sampleConversations';
import { replyToChip, replyToText, type BotReply } from './replies';
import { dotDate } from './time';
import type { ChatMessage, ChipAction, ChatText, Conversation } from './types';

// 대화 저장 방식 (마이페이지와 같은 구조)
// - guest: 로그인 전. 이 화면을 보는 동안만 메모리에 두고 저장하지 않음
// - demo: 데모 계정. 예시 대화로 시작, 바꾼 내용은 메모리에만 (탭을 닫으면 사라짐)
// - member: 실제 회원. 질문은 POST /chatbot/ask(AI)로 보내고 서버가 대화를 저장 (7d). 화면 목록은 아직 메모리
//   화면을 열면 서버의 지난 대화 목록을 불러오고(7e), 대화를 고르면 그때 메시지를 불러온다. 카드는 저장하지 않아 글만 보임
export type ChatMode = 'guest' | 'demo' | 'member';

const memory: Partial<Record<ChatMode, Conversation[]>> = {};

// 서버 에러 코드 → 화면 문구 키 (chat.api.*)
const API_ERRORS: Record<string, string> = {
  network: 'network',
  rate_limited: 'rateLimited',
  'chatbot.unavailable': 'unavailable',
  'auth.required': 'login',
  not_found: 'notFound',
  validation: 'validation',
};

// 인사말만 있는 대화는 아직 시작하지 않은 대화로 본다
const isBlank = (c: Conversation) => !c.remote && c.messages.every((m) => m.role === 'bot');

// 목록에 시작 전 대화가 하나는 있게 해서 화면을 열면 바로 입력할 수 있게 한다
const withBlank = (list: Conversation[]) => (list.some(isBlank) ? list : [newConversation(), ...list]);

function load(mode: ChatMode): Conversation[] {
  memory[mode] = withBlank(memory[mode] ?? (mode === 'demo' ? SAMPLE_CONVERSATIONS : []));
  return memory[mode]!;
}

function save(mode: ChatMode, list: Conversation[]) {
  memory[mode] = list;
  // TODO(member): 로그인·저장 백엔드가 생기면 여기서 서버에 저장
}

const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
const now = () => new Date().toISOString();

function newConversation(): Conversation {
  const at = now();
  return { id: uid(), createdAt: at, messages: [{ id: uid(), role: 'bot', text: GREETING, at }] };
}

const textOf = (x: ChatText) => (typeof x === 'string' ? x : `${x.ko} ${x.en}`);

export function useConversations() {
  const { t, i18n } = useTranslation();
  const { user, token } = useAuth();
  const mode: ChatMode = !user ? 'guest' : user.demo ? 'demo' : 'member';

  const [list, setList] = useState<Conversation[]>(() => load(mode));
  const [activeId, setActiveId] = useState<string | null>(null);

  // 로그인·로그아웃하면 그 계정의 대화로 바꿔 끼운다
  useEffect(() => {
    setList(load(mode));
    setActiveId(null);
  }, [mode]);

  const update = useCallback(
    (fn: (prev: Conversation[]) => Conversation[]) =>
      setList((prev) => {
        const next = fn(prev);
        save(mode, next);
        return next;
      }),
    [mode],
  );

  const loading = useRef(new Set<string>()); // 메시지를 불러오는 중인 대화 (같은 요청을 두 번 보내지 않게)

  // 회원: 서버의 지난 대화 목록 (이미 화면에 있는 대화는 그대로)
  useEffect(() => {
    if (mode !== 'member' || !token) return;
    let stop = false;
    listChatSessions(token)
      .then((rows) => {
        if (stop) return;
        update((prev) => {
          const known = new Set(prev.map((c) => c.serverId).filter(Boolean));
          const fromServer: Conversation[] = rows
            .filter((r) => !known.has(r.id))
            .map((r) => ({ id: r.id, serverId: r.id, createdAt: r.created_at, messages: [], remote: true }));
          return fromServer.length ? [...prev, ...fromServer] : prev;
        });
      })
      .catch(() => {}); // 목록을 못 받아도 새 대화는 할 수 있게
    return () => {
      stop = true;
    };
  }, [mode, token, update]);

  // 목록은 최근 생성순
  // (예시는 +09:00, 새 대화는 UTC 형식이라 문자열이 아닌 시각으로 비교)
  const sorted = useMemo(() => [...list].sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt)), [list]);

  // 고른 대화가 없으면 시작 전 대화를 보여준다
  const active = sorted.find((c) => c.id === activeId) ?? sorted.find(isBlank) ?? sorted[0] ?? null;

  // 회원: 서버에서만 받은 대화를 열면 메시지를 불러온다 (첫 인사 + 저장된 글)
  useEffect(() => {
    if (!active?.remote || !active.serverId || !token || loading.current.has(active.id)) return;
    const { id, serverId, createdAt } = active;
    loading.current.add(id);
    getChatSession(token, serverId)
      .then((d) =>
        update((prev) =>
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
                      ...(m.role === 'assistant' ? { ai: true } : {}),
                    })),
                  ],
                },
          ),
        ),
      )
      .catch(() => update((prev) => withBlank(prev.filter((c) => c.id !== id)))) // 서버에서 지워짐(30일 등)
      .finally(() => loading.current.delete(id));
  }, [active, token, update]);

  const startNew = () => {
    const blank = sorted.find(isBlank);
    if (blank) return setActiveId(blank.id);
    const c = newConversation();
    update((prev) => [c, ...prev]);
    setActiveId(c.id);
  };

  const remove = (id: string) => {
    const target = list.find((c) => c.id === id);
    if (mode === 'member' && token && target?.serverId) deleteChatSession(token, target.serverId).catch(() => {});
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
      patch = { text: t(`chat.api.${API_ERRORS[code] ?? 'error'}`), failed: true };
    }
    update((prev) =>
      prev.map((c) =>
        c.id !== conv.id ? c : { ...c, serverId, messages: c.messages.map((m) => (m.id === waitId ? { ...m, ...patch, pending: false } : m)) },
      ),
    );
  };

  const busy = !!active?.messages.some((m) => m.pending);
  const shown = (x: ChatText) => (typeof x === 'string' ? x : i18n.language === 'ko' ? x.ko : x.en);

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

  return { mode, busy, conversations: sorted, active, select: setActiveId, startNew, remove, send, choose, search };
}
