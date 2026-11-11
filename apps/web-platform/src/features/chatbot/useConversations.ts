import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../components/auth';
import { GREETING, SAMPLE_CONVERSATIONS } from './sampleConversations';
import { replyToChip, replyToText, type BotReply } from './replies';
import { dotDate } from './time';
import type { ChatMessage, ChipAction, ChatText, Conversation } from './types';

// 대화 저장 방식 (마이페이지와 같은 구조)
// - guest: 로그인 전. 이 화면을 보는 동안만 메모리에 두고 저장하지 않음
// - demo: 데모 계정. 예시 대화로 시작, 바꾼 내용은 메모리에만 (탭을 닫으면 사라짐)
// - member: 실제 회원. 백엔드 연결 전이라 지금은 메모리, 연결 후 save()에서 서버 저장
export type ChatMode = 'guest' | 'demo' | 'member';

const memory: Partial<Record<ChatMode, Conversation[]>> = {};

// 인사말만 있는 대화는 아직 시작하지 않은 대화로 본다
const isBlank = (c: Conversation) => c.messages.every((m) => m.role === 'bot');

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
  const { t } = useTranslation();
  const { user } = useAuth();
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

  // 목록은 최근 생성순
  // (예시는 +09:00, 새 대화는 UTC 형식이라 문자열이 아닌 시각으로 비교)
  const sorted = useMemo(() => [...list].sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt)), [list]);

  // 고른 대화가 없으면 시작 전 대화를 보여준다
  const active = sorted.find((c) => c.id === activeId) ?? sorted.find(isBlank) ?? sorted[0] ?? null;

  const startNew = () => {
    const blank = sorted.find(isBlank);
    if (blank) return setActiveId(blank.id);
    const c = newConversation();
    update((prev) => [c, ...prev]);
    setActiveId(c.id);
  };

  const remove = (id: string) => {
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

  const send = (text: string) => {
    if (!active || !text.trim()) return;
    push(active.id, text.trim(), replyToText(t, text));
  };

  const choose = (label: ChatText, action: ChipAction) => {
    if (!active) return;
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

  return { mode, conversations: sorted, active, select: setActiveId, startNew, remove, send, choose, search };
}
