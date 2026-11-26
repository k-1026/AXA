// 수기 예약 (전화·방문 접수처럼 병원이 직접 넣는 예약) 저장소
// 지금은 백엔드 API가 없어 이 브라우저(localStorage)에만 저장 → 다른 기기·직원에게는 안 보임
// 백엔드가 생기면 이 파일의 list·save·remove만 API 호출로 바꾸면 됨 (화면 코드는 그대로)
export type ManualStatus = 'confirmed' | 'visited' | 'no_show' | 'cancelled';
export type ManualBooking = {
  id: string;
  slot: string; // ISO (UTC)
  name: string; // 환자 표시 이름 또는 메모용 호칭 (실명 대신 이니셜 권장)
  treatment: string;
  memo: string;
  status: ManualStatus;
};

const KEY = 'md.dashboard.manualBookings';

function read(): ManualBooking[] {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as ManualBooking[]) : [];
  } catch {
    return [];
  }
}

function write(list: ManualBooking[]) {
  try { localStorage.setItem(KEY, JSON.stringify(list)); } catch { /* 저장 못 하는 환경(사생활 보호 창 등): 이번 화면에서만 유지 */ }
}

export async function listManual(): Promise<ManualBooking[]> {
  return read();
}

export async function saveManual(b: Omit<ManualBooking, 'id'> & { id?: string }): Promise<ManualBooking> {
  const list = read();
  const item: ManualBooking = { ...b, id: b.id ?? `M-${Date.now().toString(36).toUpperCase()}` };
  const i = list.findIndex((x) => x.id === item.id);
  if (i >= 0) list[i] = item; else list.push(item);
  write(list);
  return item;
}

export async function removeManual(id: string): Promise<void> {
  write(read().filter((x) => x.id !== id));
}
