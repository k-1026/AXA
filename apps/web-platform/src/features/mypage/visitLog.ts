import { useSyncExternalStore } from 'react';
import { createAccountList } from '../../components/account';
import { uid } from '../../lib/common';

// 방문 기록(개인 다이어리). 본인만 쓰고 본인만 본다: 후기가 아니므로 서버로 보내거나 병원 화면에 표시하지 않는다
// 2026-11-26: 방문한 병원·날짜는 예약(병원이 "방문 완료" 표시한 건)에서 자동으로 가져오고, 환자는 "나의 경험"만 쓴다
//   → 기록은 예약 메시지 id(bookingId)에 붙는다. bookingId 없는 예전 직접 입력 기록은 화면에 쓰지 않음
interface VisitRecord {
  id: string;
  bookingId?: string; // 방문 완료된 예약 (상담 메시지 id)
  hospitalId?: string;
  hospitalName: string;
  date: string; // YYYY-MM-DD
  note: string;
  createdAt: string;
}

export type VisitInput = Pick<VisitRecord, 'bookingId' | 'hospitalId' | 'hospitalName' | 'date' | 'note'>;

// 계정별로 따로 저장 (로그인 전·데모·회원마다 다른 기록). 탈퇴하면 그 계정 기록은 지움
const store = createAccountList<VisitRecord>('visitLog');

// 예약 1건에 경험 1개: 있으면 고치고 없으면 새로 만든다
const saveNote = (input: VisitInput & { bookingId: string }) => {
  const list = store.get();
  const found = list.find((r) => r.bookingId === input.bookingId);
  store.set(
    found
      ? list.map((r) => (r === found ? { ...r, ...input } : r))
      : [...list, { ...input, id: uid(), createdAt: new Date().toISOString() }],
  );
};
const removeNote = (bookingId: string) => store.set(store.get().filter((r) => r.bookingId !== bookingId));

export function useVisitLog() {
  const visits = useSyncExternalStore(store.subscribe, store.get);
  const noteFor = (bookingId: string) => visits.find((r) => r.bookingId === bookingId)?.note ?? '';
  return { visits, noteFor, saveNote, removeNote };
}
