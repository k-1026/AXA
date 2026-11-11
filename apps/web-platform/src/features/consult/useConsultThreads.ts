import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../../components/auth';
import { SAMPLE_THREADS } from './sampleThreads';
import type { BookingRequest, ConsultThread } from './types';
import type { ChatText } from '../chatbot/types';

// 저장 방식은 챗봇과 같음 (백엔드 연결 전)
// - demo: 예시 상담으로 시작, 바꾼 내용은 메모리에만
// - member: 빈 목록으로 시작, 지금은 메모리. 연결 후 save()에서 서버 저장
// 병원 답변은 병원 담당자가 직접 쓴다. 이 화면은 답을 지어내지 않는다
type Mode = 'demo' | 'member';
const memory: Partial<Record<Mode, ConsultThread[]>> = {};

const load = (mode: Mode) => (memory[mode] ??= mode === 'demo' ? SAMPLE_THREADS : []);
const save = (mode: Mode, list: ConsultThread[]) => {
  memory[mode] = list;
  // TODO(member): 상담 백엔드가 생기면 여기서 서버에 저장
};

const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
const lastAt = (t: ConsultThread) => t.messages[t.messages.length - 1]?.at ?? '';
const textOf = (x?: ChatText) => (!x ? '' : typeof x === 'string' ? x : `${x.ko} ${x.en}`);

export type NewThread = Omit<ConsultThread, 'messages' | 'unread'>;

export function useConsultThreads() {
  const { user } = useAuth();
  const mode: Mode = user?.demo ? 'demo' : 'member';
  const [list, setList] = useState<ConsultThread[]>(() => load(mode));
  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    setList(load(mode));
    setActiveId(null);
  }, [mode]);

  const update = useCallback(
    (fn: (prev: ConsultThread[]) => ConsultThread[]) =>
      setList((prev) => {
        const next = fn(prev);
        save(mode, next);
        return next;
      }),
    [mode],
  );

  // 최근 대화가 있는 병원이 위로 (메시지가 없는 새 상담은 맨 위)
  const threads = useMemo(
    () => [...list].sort((a, b) => (Date.parse(lastAt(b)) || Infinity) - (Date.parse(lastAt(a)) || Infinity)),
    [list],
  );
  const active = threads.find((t) => t.hospitalId === activeId) ?? threads[0] ?? null;

  // 상담을 열면 병원 답변을 읽은 것으로 처리
  const select = (id: string) => {
    setActiveId(id);
    update((prev) => prev.map((t) => (t.hospitalId === id && t.unread ? { ...t, unread: 0 } : t)));
  };

  // 같은 병원 상담이 이미 있으면 그 상담을 연다 (병원당 하나)
  const open = (thread: NewThread) => {
    update((prev) => (prev.some((t) => t.hospitalId === thread.hospitalId) ? prev : [{ ...thread, messages: [], unread: 0 }, ...prev]));
    setActiveId(thread.hospitalId);
  };

  const append = (id: string, msg: { text?: string; booking?: BookingRequest }) =>
    update((prev) =>
      prev.map((t) =>
        t.hospitalId === id ? { ...t, messages: [...t.messages, { id: uid(), from: 'user', at: new Date().toISOString(), ...msg }] } : t,
      ),
    );

  const editBooking = (id: string, messageId: string, fn: (b: BookingRequest) => BookingRequest) =>
    update((prev) =>
      prev.map((t) =>
        t.hospitalId === id ? { ...t, messages: t.messages.map((m) => (m.id === messageId && m.booking ? { ...m, booking: fn(m.booking) } : m)) } : t,
      ),
    );

  // 변경하면 병원이 다시 확인해야 하므로 확인 대기로 돌아간다 (예약번호도 새로 받음)
  const changeBooking = (id: string, messageId: string, b: Omit<BookingRequest, 'status'>, notice: string) => {
    editBooking(id, messageId, (old) => ({ ...old, ...b, status: 'pending', bookingNo: undefined }));
    append(id, { text: notice });
  };

  const cancelBooking = (id: string, messageId: string, notice: string) => {
    editBooking(id, messageId, (old) => ({ ...old, status: 'cancelled', cancelledAt: new Date().toISOString() }));
    append(id, { text: notice });
  };

  const send = (text: string) => active && text.trim() && append(active.hospitalId, { text: text.trim() });
  const requestBooking = (b: Omit<BookingRequest, 'status'>) => active && append(active.hospitalId, { booking: { ...b, status: 'pending' } });

  const search = (q: string) => {
    const s = q.trim().toLowerCase();
    if (!s) return threads;
    return threads.filter((t) => textOf(t.name).toLowerCase().includes(s) || t.messages.some((m) => textOf(m.text).toLowerCase().includes(s)));
  };

  const bookings = threads.flatMap((t) => t.messages.filter((m) => m.booking).map((m) => ({ thread: t, message: m, booking: m.booking! })));

  return { mode, threads, active, select, open, send, requestBooking, changeBooking, cancelBooking, search, bookings };
}
