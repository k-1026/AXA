// 상담·예약 공용: 병원 예약 API 호출 · 코드→글자 · 한국 시간 · 예약 처리 폼 (캘린더·요청 목록·상담 채팅이 같이 씀)
import { useState } from 'react';
import { API_BASE } from '../../../components/api';
import { readStaffToken } from '../../../features/staff/staffSession';
import { clearStaffGet, staffGet } from './staffGet';

export type DbReq = {
  id: string; status: string; nationality: string; lang: string; department_code?: string; treatment: string | null; visa_needed: boolean;
  preferred_slots: string[]; confirmed_slot: string | null; created_at: string;
  paid_amount?: number | null; paid_method?: string | null; // 결제 확인 (paid, 11/27)
  message_original: string | null; message_translated: string | null;
  replies?: { text_ko: string; text_translated: string | null; sent_at: string }[];
  questions?: { text_original: string; text_translated: string | null; created_at: string }[];
};
export type ActionMode = 'confirm' | 'propose' | 'reject' | 'visited' | 'no_show';

export const DB_STATUSES = ['pending', 'proposed', 'confirmed', 'visited', 'no_show', 'paid'] as const;
export const ST: Record<string, string> = {
  pending: '대기', proposed: '시간 제안함', confirmed: '확정', visited: '방문 완료', no_show: '미방문', paid: '결제 확인', cancelled: '취소', rejected: '거절',
};
export const NAT: Record<string, string> = { KR: '한국', TW: '대만', CN: '중국', JP: '일본', MN: '몽골', VN: '베트남', US: '미국', TH: '태국' };
export const LANG: Record<string, string> = { 'zh-TW': '번체', 'zh-CN': '간체', en: '영어', vi: '베트남어', ja: '일본어', ko: '한국어' };
export const DEPT: Record<string, string> = { dermatology: '피부과', plastic: '성형외과', ophthalmology: '안과', internal: '내과', dental: '치과', korean_medicine: '한방' };
export const TRT: Record<string, string> = { laser_toning: '레이저 토닝', acne_scar: '여드름 흉터', botox: '보톡스', melasma: '기미 치료', filler: '필러' };
export const REJECT: Record<string, string> = { fully_booked: '예약이 마감됐어요', not_offered: '하지 않는 진료예요', needs_consult: '대면 상담이 먼저 필요해요', other: '기타' };
export const ERR: Record<string, string> = {
  'booking.invalid_transition': '이미 다른 상태로 바뀐 예약이에요. 목록을 새로 불러왔어요',
  validation: '입력값을 확인해 주세요', not_found: '예약을 찾을 수 없어요 (다른 곳에서 바뀌었을 수 있어요)',
  'auth.forbidden': '이 계정으로는 할 수 없어요',
};
export const TIMES = Array.from({ length: 21 }, (_, i) => `${String(9 + Math.floor(i / 2)).padStart(2, '0')}:${i % 2 ? '30' : '00'}`); // 09:00~19:00

// ---------- 한국 날짜·시간 ----------
export const kday = (iso: string) => new Date(new Date(iso).getTime() + 9 * 3600e3).toISOString().slice(0, 10);
export const khm = (iso: string) => new Date(new Date(iso).getTime() + 9 * 3600e3).toISOString().slice(11, 16);
export const toIso = (d: string, t: string) => new Date(`${d}T${t}:00+09:00`).toISOString();
export const todayKst = () => kday(new Date().toISOString());
export const md = (d: string) => `${+d.slice(5, 7)}월 ${+d.slice(8)}일`;
export const WEEK = ['월', '화', '수', '목', '금', '토', '일'];
export const dow = (d: string) => WEEK[(new Date(d + 'T00:00:00Z').getUTCDay() + 6) % 7];
export const slotLabel = (iso: string) => `${md(kday(iso))}(${dow(kday(iso))}) ${khm(iso)}`;


export const reqId = (r: DbReq) => `R-${r.id.slice(0, 4).toUpperCase()}`;
export const reqWho = (r: DbReq) => `${NAT[r.nationality] || r.nationality} · ${LANG[r.lang] || r.lang}`;
// 시술명이 없으면 진료과로 (예약 화면에서 진료과만 고른 요청)
export const reqTitle = (r: DbReq) => TRT[r.treatment ?? ''] || r.treatment || (r.department_code ? `${DEPT[r.department_code] || r.department_code} 상담` : '상담');
// 상태별 병원이 할 수 있는 처리 (백엔드 TRANSITIONS와 같게: 시간 제안한 건은 환자가 수락해야 확정)
export const ACTIONS: Record<string, { mode: ActionMode; label: string }[]> = {
  pending: [{ mode: 'confirm', label: '확정' }, { mode: 'propose', label: '시간 제안' }, { mode: 'reject', label: '거절' }],
  proposed: [{ mode: 'propose', label: '다시 제안' }, { mode: 'reject', label: '거절' }],
  confirmed: [{ mode: 'visited', label: '방문 완료' }, { mode: 'no_show', label: '미방문' }],
};

export class Expired extends Error {}
// GET은 여러 카드가 같이 쓰도록 묶어서 (staffGet), 처리(POST 등) 뒤에는 묶어 둔 값을 비움
export async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let status: number, ok: boolean, body: { code?: string };
  if (!init?.method || init.method === 'GET') {
    ({ status, ok, body } = await staffGet(path));
  } else {
    const token = readStaffToken();
    const res = await fetch(API_BASE + path, {
      ...init,
      headers: { Authorization: 'Bearer ' + token, ...(init?.body ? { 'Content-Type': 'application/json' } : {}) },
    });
    clearStaffGet();
    ({ status, ok } = res);
    body = await res.json().catch(() => ({}));
  }
  if (status === 401) throw new Expired();
  if (!ok) throw new Error(body.code || String(status));
  return body as T;
}


// 처리 실행: 성공하면 알림 문구, 실패하면 에러 코드 → 글자
export async function runAction(r: DbReq, action: ActionMode, body: object) {
  return call(`/tenant/booking-requests/${r.id}/${action === 'no_show' ? 'no-show' : action}`, { method: 'POST', body: JSON.stringify(body) });
}
export const errText = (code: string) => ERR[code] || `저장하지 못했어요: ${code}`;

export // DB 예약 처리 폼 (확정할 시간 고르기 · 제안할 시간 · 거절 사유 · 방문/미방문 확인)
function ActionForm({ req, mode, day, busy, onCancel, act }: {
  req: DbReq; mode: ActionMode; day: string; busy: boolean; onCancel: () => void;
  act: (req: DbReq, action: ActionMode, body: object, done: string) => Promise<void>;
}) {
  const [slot, setSlot] = useState(req.preferred_slots[0] ?? '');
  const [d, setD] = useState(day < todayKst() ? todayKst() : day);
  const [t, setT] = useState('10:00');
  const [reason, setReason] = useState('');
  const [err, setErr] = useState('');

  const submit = () => {
    setErr('');
    if (mode === 'confirm') {
      if (!slot) return setErr('확정할 시간을 골라 주세요');
      return act(req, 'confirm', { slot }, `예약을 확정했어요: ${slotLabel(slot)}`);
    }
    if (mode === 'propose') {
      const iso = toIso(d, t);
      if (new Date(iso) <= new Date()) return setErr('지난 시간은 고를 수 없어요');
      return act(req, 'propose', { slot: iso }, `다른 시간을 제안했어요: ${slotLabel(iso)}`);
    }
    if (mode === 'reject') {
      if (!reason) return setErr('거절 사유를 골라 주세요');
      return act(req, 'reject', { reason }, '요청을 거절했어요');
    }
    return act(req, mode, {}, mode === 'visited' ? '방문 완료로 바꿨어요' : '미방문으로 바꿨어요');
  };

  return (
    <div className="day-panel">
      {mode === 'confirm' && (
        <fieldset>
          <legend>확정할 시간 (환자 희망)</legend>
          {req.preferred_slots.map((s, i) => (
            <label key={s} className="opt"><input type="radio" name="slot" checked={slot === s} onChange={() => setSlot(s)} /> {slotLabel(s)} <small>희망 {i + 1}</small></label>
          ))}
        </fieldset>
      )}
      {mode === 'propose' && (
        <div className="pick">
          <span>제안할 시간</span>
          <input type="date" value={d} min={todayKst()} onChange={(e) => setD(e.target.value)} aria-label="날짜" />
          <select value={t} onChange={(e) => setT(e.target.value)} aria-label="시간">{TIMES.map((x) => <option key={x}>{x}</option>)}</select>
          <small>환자가 수락하면 확정돼요 · 진료시간 밖이면 서버가 거절해요</small>
        </div>
      )}
      {mode === 'reject' && (
        <label className="pick"><span>거절 사유</span>
          <select value={reason} onChange={(e) => setReason(e.target.value)}>
            <option value="">사유를 골라 주세요</option>
            {Object.entries(REJECT).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
      )}
      {(mode === 'visited' || mode === 'no_show') && (
        <p className="note">확정 시간 {req.confirmed_slot ? slotLabel(req.confirmed_slot) : '—'} 예약을 {mode === 'visited' ? '방문 완료' : '미방문'}로 바꿀까요?{mode === 'no_show' && ' 되돌릴 수 없어요.'}</p>
      )}
      {err && <p className="dlg-err">{err}</p>}
      <div className="day-acts">
        <button type="button" className="btn-ghost" onClick={onCancel} disabled={busy}>취소</button>
        <button type="button" className={mode === 'reject' || mode === 'no_show' ? 'btn is-danger' : 'btn'} onClick={submit} disabled={busy}>
          {busy ? '처리 중…' : ({ confirm: '예약 확정', propose: '시간 제안 보내기', reject: '거절', visited: '방문 완료', no_show: '미방문', manual: '' } as const)[mode]}
        </button>
      </div>
    </div>
  );
}


// 처리 중인 요청(대기·시간 제안함·확정) — 요청 목록·상담 채팅이 씀. 확정은 진료일 순
export async function loadOpenRequests(): Promise<DbReq[]> {
  const [p, q, c] = await Promise.all((['pending', 'proposed', 'confirmed'] as const).map((s) => call<DbReq[]>(`/tenant/booking-requests?status=${s}`)));
  return [...p, ...q, ...c.sort((a, b) => String(a.confirmed_slot).localeCompare(String(b.confirmed_slot)))];
}

// 처리 폼을 띄우는 작은 창 (요청 목록·상담 채팅에서 버튼을 누르면)
export function ActionDialog({ req, mode, onClose, onDone, onExpired }: {
  req: DbReq; mode: ActionMode; onClose: () => void; onDone: (msg: string) => void; onExpired: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const act = async (r: DbReq, action: ActionMode, body: object, done: string) => {
    setBusy(true); setErr('');
    try {
      await runAction(r, action, body);
      onDone(done);
    } catch (e) {
      if (e instanceof Expired) { onExpired(); return; }
      const code = (e as Error).message;
      // 이미 바뀐 요청이면 안내만 보여 주고, 창을 닫을 때 목록을 다시 불러옴 (onClose → 부모가 새로고침)
      setErr(code === 'booking.invalid_transition' || code === 'not_found' ? errText(code).replace('목록을 새로 불러왔어요', '창을 닫으면 목록을 새로 불러와요') : errText(code));
    } finally {
      setBusy(false);
    }
  };
  const label = ACTIONS[req.status]?.find((a) => a.mode === mode)?.label ?? '';
  const day = req.status === 'pending' ? kday(req.preferred_slots[0] ?? new Date().toISOString()) : kday(req.confirmed_slot ?? new Date().toISOString());
  return (
    <div className="dlg-wrap" onClick={(e) => { if (e.target === e.currentTarget && !busy) onClose(); }}>
      <div className="dlg" role="dialog" aria-modal="true" aria-label={label}>
        <header className="dlg-head">
          <h3>{reqId(req)} · {label}</h3>
          <button type="button" className="btn-ghost" onClick={onClose} disabled={busy} aria-label="닫기">✕</button>
        </header>
        <p className="mini">{reqWho(req)} · {reqTitle(req)} · {ST[req.status]}</p>
        {err && <p className="dlg-err" role="alert">{err}</p>}
        <ActionForm req={req} mode={mode} day={day} busy={busy} onCancel={onClose} act={act} />
      </div>
    </div>
  );
}
