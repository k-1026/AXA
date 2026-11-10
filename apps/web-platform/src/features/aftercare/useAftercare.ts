import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../../components/auth';
import { useConsultThreads } from '../consult/useConsultThreads';
import { SAMPLE_AFTERCARE } from './sampleAftercare';
import type { AftercareMessage, Attachment } from './types';

// 사후 관리 대상 = 병원이 방문 완료로 표시한 예약만 (예약 내역 기반)
// 저장 방식은 상담과 같음: demo는 예시로 시작해 메모리에만, member는 백엔드 연결 전까지 메모리
type Mode = 'demo' | 'member';
type Store = Record<string, { messages: AftercareMessage[]; unread: number }>;
const memory: Partial<Record<Mode, Store>> = {};
const load = (mode: Mode): Store => (memory[mode] ??= mode === 'demo' ? SAMPLE_AFTERCARE : {});

const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

export function useAftercare() {
  const { user } = useAuth();
  const mode: Mode = user?.demo ? 'demo' : 'member';
  const consult = useConsultThreads();
  const [store, setStore] = useState<Store>(() => load(mode));
  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    setStore(load(mode));
    setActiveId(null);
  }, [mode]);

  const update = useCallback(
    (fn: (prev: Store) => Store) =>
      setStore((prev) => {
        const next = fn(prev);
        memory[mode] = next;
        // TODO(member): 백엔드가 생기면 여기서 서버 저장 (사진·영상은 서버에 올린 주소로 교체)
        return next;
      }),
    [mode],
  );

  // 방문일이 최근인 순
  const visits = useMemo(
    () =>
      consult.bookings
        .filter((b) => b.booking.status === 'completed')
        .map((b) => ({ id: b.message.id, thread: b.thread, booking: b.booking, ...(store[b.message.id] ?? { messages: [], unread: 0 }) }))
        .sort((a, b) => `${b.booking.date}T${b.booking.time}`.localeCompare(`${a.booking.date}T${a.booking.time}`)),
    [consult.bookings, store],
  );
  const active = visits.find((v) => v.id === activeId) ?? visits[0] ?? null;

  const select = (id: string) => {
    setActiveId(id);
    update((prev) => (prev[id]?.unread ? { ...prev, [id]: { ...prev[id], unread: 0 } } : prev));
  };

  const send = (text: string, attachments: Attachment[]) => {
    if (!active || (!text.trim() && !attachments.length)) return;
    const msg: AftercareMessage = { id: uid(), from: 'user', at: new Date().toISOString(), text: text.trim() || undefined, attachments: attachments.length ? attachments : undefined };
    update((prev) => {
      const cur = prev[active.id] ?? { messages: [], unread: 0 };
      return { ...prev, [active.id]: { ...cur, messages: [...cur.messages, msg] } };
    });
  };

  return { mode, visits, active, select, send };
}
