// 상담·예약 "예약 캘린더" (운영 후 모드). 옛 /dashboard/legacy 주 단위 캘린더를 월 단위로, 새 디자인으로
// - 환자 예약(DB): GET /tenant/booking-requests?status=… → 대기는 환자 희망 1순위 시간, 나머지는 확정 시간에 표시
// - 날짜를 누르면 팝업: 그날 예약 목록 + DB 예약 처리(확정·시간 제안·거절·방문 완료·미방문, POST /tenant/booking-requests/{id}/{action})
//   + 수기 예약 추가·수정·삭제 (manualBookings.ts, 지금은 이 브라우저에만 저장)
import { useCallback, useEffect, useMemo, useState } from 'react';
import { API_BASE } from '../../../components/api';
import { readStaffToken } from '../../../features/staff/staffSession';
import { listManual, removeManual, saveManual, type ManualBooking, type ManualStatus } from './manualBookings';

type DbReq = {
  id: string; status: string; nationality: string; lang: string; treatment: string | null;
  preferred_slots: string[]; confirmed_slot: string | null; message_translated: string | null;
};
type Ev =
  | { kind: 'db'; key: string; slot: string; status: string; label: string; who: string; req: DbReq }
  | { kind: 'manual'; key: string; slot: string; status: ManualStatus; label: string; who: string; m: ManualBooking };

const DB_STATUSES = ['pending', 'proposed', 'confirmed', 'visited', 'no_show'] as const;
const ST: Record<string, string> = {
  pending: '대기', proposed: '시간 제안함', confirmed: '확정', visited: '방문 완료', no_show: '미방문', cancelled: '취소', rejected: '거절',
};
const NAT: Record<string, string> = { TW: '대만', CN: '중국', JP: '일본', MN: '몽골', VN: '베트남', US: '미국', TH: '태국' };
const LANG: Record<string, string> = { 'zh-TW': '번체', 'zh-CN': '간체', en: '영어', vi: '베트남어', ja: '일본어', ko: '한국어' };
const TRT: Record<string, string> = { laser_toning: '레이저 토닝', acne_scar: '여드름 흉터', botox: '보톡스', melasma: '기미 치료', filler: '필러' };
const REJECT: Record<string, string> = { fully_booked: '예약이 마감됐어요', not_offered: '하지 않는 진료예요', needs_consult: '대면 상담이 먼저 필요해요', other: '기타' };
const ERR: Record<string, string> = {
  'booking.invalid_transition': '이미 다른 상태로 바뀐 예약이에요. 목록을 새로 불러왔어요',
  validation: '입력값을 확인해 주세요', not_found: '예약을 찾을 수 없어요 (다른 곳에서 바뀌었을 수 있어요)',
  'auth.forbidden': '이 계정으로는 할 수 없어요',
};
const TIMES = Array.from({ length: 21 }, (_, i) => `${String(9 + Math.floor(i / 2)).padStart(2, '0')}:${i % 2 ? '30' : '00'}`); // 09:00~19:00

// ---------- 한국 날짜·시간 ----------
const kday = (iso: string) => new Date(new Date(iso).getTime() + 9 * 3600e3).toISOString().slice(0, 10);
const khm = (iso: string) => new Date(new Date(iso).getTime() + 9 * 3600e3).toISOString().slice(11, 16);
const toIso = (d: string, t: string) => new Date(`${d}T${t}:00+09:00`).toISOString();
const todayKst = () => kday(new Date().toISOString());
const md = (d: string) => `${+d.slice(5, 7)}월 ${+d.slice(8)}일`;
const WEEK = ['월', '화', '수', '목', '금', '토', '일'];
const dow = (d: string) => WEEK[(new Date(d + 'T00:00:00Z').getUTCDay() + 6) % 7];
const slotLabel = (iso: string) => `${md(kday(iso))}(${dow(kday(iso))}) ${khm(iso)}`;

// 그 달 칸 (월요일 시작, 앞뒤 달 날짜로 채움)
function monthCells(ym: string): string[] {
  const first = new Date(ym + '-01T00:00:00Z');
  const start = new Date(first.getTime() - ((first.getUTCDay() + 6) % 7) * 864e5);
  const last = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0));
  const end = new Date(last.getTime() + ((7 - last.getUTCDay()) % 7) * 864e5);
  const out: string[] = [];
  for (let t = start.getTime(); t <= end.getTime(); t += 864e5) out.push(new Date(t).toISOString().slice(0, 10));
  return out;
}
const shiftMonth = (ym: string, n: number) => {
  const d = new Date(ym + '-01T00:00:00Z');
  d.setUTCMonth(d.getUTCMonth() + n);
  return d.toISOString().slice(0, 7);
};

class Expired extends Error {}
async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const token = readStaffToken();
  const res = await fetch(API_BASE + path, {
    ...init,
    headers: { Authorization: 'Bearer ' + token, ...(init?.body ? { 'Content-Type': 'application/json' } : {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (res.status === 401) throw new Expired();
  if (!res.ok) throw new Error(body.code || String(res.status));
  return body as T;
}

function toEvents(db: DbReq[], manual: ManualBooking[]): Ev[] {
  const evs: Ev[] = [];
  for (const r of db) {
    const slot = r.status === 'pending' ? r.preferred_slots[0] : r.confirmed_slot;
    if (!slot) continue;
    evs.push({
      kind: 'db', key: r.id, slot, status: r.status, req: r,
      label: TRT[r.treatment ?? ''] || r.treatment || '상담',
      who: `R-${r.id.slice(0, 4).toUpperCase()} · ${NAT[r.nationality] || r.nationality} · ${LANG[r.lang] || r.lang}`,
    });
  }
  for (const m of manual) evs.push({ kind: 'manual', key: m.id, slot: m.slot, status: m.status, m, label: m.treatment || '수기 예약', who: m.name || '이름 없음' });
  return evs.sort((a, b) => a.slot.localeCompare(b.slot));
}

export default function BookingCalendar({ onExpired, onChanged }: { onExpired: () => void; onChanged?: () => void }) {
  const [ym, setYm] = useState(() => todayKst().slice(0, 7));
  const [db, setDb] = useState<DbReq[]>([]);
  const [manual, setManual] = useState<ManualBooking[]>([]);
  const [state, setState] = useState<'loading' | 'ok' | 'error'>('loading');
  const [day, setDay] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [lists, m] = await Promise.all([
        Promise.all(DB_STATUSES.map((s) => call<DbReq[]>(`/tenant/booking-requests?status=${s}`))),
        listManual(),
      ]);
      setDb(lists.flat());
      setManual(m);
      setState('ok');
    } catch (e) {
      if (e instanceof Expired) onExpired(); else setState('error');
    }
  }, [onExpired]);

  useEffect(() => { if (readStaffToken()) load(); }, [load]);

  const events = useMemo(() => toEvents(db, manual), [db, manual]);
  const byDay = useMemo(() => {
    const m = new Map<string, Ev[]>();
    for (const e of events) { const d = kday(e.slot); m.set(d, [...(m.get(d) ?? []), e]); }
    return m;
  }, [events]);
  const cells = monthCells(ym);
  const today = todayKst();
  const refresh = async () => { await load(); onChanged?.(); };

  return (
    <section className="card card-wide">
      <header className="card-head">
        <span className="badge badge-live">실제</span>
        <h3>예약 캘린더</h3>
        <div className="cal-nav">
          <button type="button" className="btn-ghost" onClick={() => setYm(shiftMonth(ym, -1))} aria-label="지난달">‹</button>
          <b>{ym.slice(0, 4)}년 {+ym.slice(5)}월</b>
          <button type="button" className="btn-ghost" onClick={() => setYm(shiftMonth(ym, 1))} aria-label="다음 달">›</button>
          <button type="button" className="btn-ghost" onClick={() => setYm(today.slice(0, 7))}>오늘</button>
        </div>
      </header>
      <p className="cal-legend">
        {['pending', 'proposed', 'confirmed', 'visited', 'no_show'].map((s) => <span key={s}><i className={`ev-dot st-${s}`} />{ST[s]}</span>)}
        <span><i className="ev-dot st-manual" />수기 예약</span>
        <span className="cal-hint">{state === 'error' ? '서버에서 불러오지 못했어요' : state === 'loading' ? '불러오는 중…' : '날짜를 누르면 예약 추가·처리'}</span>
      </p>
      <div className="cal-wrap">
      <div className="cal" role="grid" aria-label={`${ym} 예약`}>
        {WEEK.map((w, i) => <div key={w} className={`cal-wd${i >= 5 ? ' is-weekend' : ''}`} role="columnheader">{w}</div>)}
        {cells.map((d) => {
          const evs = byDay.get(d) ?? [];
          const out = d.slice(0, 7) !== ym;
          return (
            <button type="button" key={d} role="gridcell" onClick={() => setDay(d)}
              className={`cal-day${out ? ' is-out' : ''}${d === today ? ' is-today' : ''}${d < today ? ' is-past' : ''}`}
              aria-label={`${md(d)} 예약 ${evs.length}건`}>
              <span className="cal-num">{+d.slice(8)}{d === today && <small> 오늘</small>}</span>
              {evs.slice(0, 3).map((e) => (
                <span key={e.key} className={`ev st-${e.kind === 'manual' ? 'manual' : e.status}`} title={`${ST[e.status]} · ${e.who}`}>
                  {khm(e.slot)} {e.label}
                </span>
              ))}
              {evs.length > 3 && <span className="ev-more">+{evs.length - 3}건</span>}
            </button>
          );
        })}
      </div>

      {/* 오른쪽: 오늘 일정 (요일 한 칸 너비, 캘린더와 같은 높이 — 넘치면 안에서 스크롤) */}
      <aside className="cal-today" aria-label="오늘 일정">
        <div className="cal-today-in">
          <p className="cal-today-head"><b>오늘 일정</b><small>{md(today)} ({dow(today)}) · {(byDay.get(today) ?? []).length}건</small></p>
          {(byDay.get(today) ?? []).length ? (
            <ul className="cal-today-list">
              {(byDay.get(today) ?? []).map((e) => (
                <li key={e.key}>
                  <button type="button" className={`st-${e.kind === 'manual' ? 'manual' : e.status}`} onClick={() => setDay(today)} title={e.who}>
                    <b>{khm(e.slot)}</b>
                    <span>{e.label}</span>
                    <small>{ST[e.status]}{e.kind === 'manual' ? ' · 수기' : ''}</small>
                  </button>
                </li>
              ))}
            </ul>
          ) : <p className="cal-today-empty">{state === 'loading' ? '불러오는 중…' : '오늘 예약이 없어요'}</p>}
          <button type="button" className="btn-ghost cal-today-add" onClick={() => setDay(today)}>+ 오늘 예약 추가</button>
        </div>
      </aside>
      </div>
      <p className="mini">대기는 환자 희망 1순위 시간, 나머지는 확정 시간 기준 · 수기 예약은 지금은 이 브라우저에만 저장돼요 (백엔드 연결 전)</p>

      {day && (
        <DayDialog day={day} events={byDay.get(day) ?? []} onClose={() => setDay(null)} onExpired={onExpired} refresh={refresh} />
      )}
    </section>
  );
}

// ---------- 날짜 팝업 ----------
type Panel = { ev?: Ev; mode: 'confirm' | 'propose' | 'reject' | 'visited' | 'no_show' | 'manual' } | null;

function DayDialog({ day, events, onClose, onExpired, refresh }: {
  day: string; events: Ev[]; onClose: () => void; onExpired: () => void; refresh: () => Promise<void>;
}) {
  const [panel, setPanel] = useState<Panel>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [toast, setToast] = useState('');

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape' && !busy) onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [busy, onClose]);

  const run = async (fn: () => Promise<unknown>, done: string) => {
    setBusy(true); setErr('');
    try {
      await fn();
      await refresh(); // 목록을 다시 불러온 뒤에 닫고 알림 (그 전에 닫으면 잠깐 빈 목록이 보임)
      setPanel(null); setToast(done);
    } catch (e) {
      if (e instanceof Expired) { onExpired(); return; }
      const code = (e as Error).message;
      setErr(ERR[code] || `저장하지 못했어요: ${code}`);
      if (code === 'booking.invalid_transition' || code === 'not_found') await refresh();
    } finally {
      setBusy(false);
    }
  };
  const act = (ev: Ev & { kind: 'db' }, action: string, body: object, done: string) =>
    run(() => call(`/tenant/booking-requests/${ev.req.id}/${action === 'no_show' ? 'no-show' : action}`, { method: 'POST', body: JSON.stringify(body) }), done);

  const actionsFor = (ev: Ev) => {
    if (ev.kind === 'manual') return [{ mode: 'manual' as const, label: '수정' }];
    return ({
      pending: [{ mode: 'confirm', label: '확정' }, { mode: 'propose', label: '시간 제안' }, { mode: 'reject', label: '거절' }],
      proposed: [{ mode: 'propose', label: '다시 제안' }, { mode: 'reject', label: '거절' }],
      confirmed: [{ mode: 'visited', label: '방문 완료' }, { mode: 'no_show', label: '미방문' }],
    } as Record<string, { mode: NonNullable<Panel>['mode']; label: string }[]>)[ev.status] ?? [];
  };

  return (
    <div className="dlg-wrap" onClick={(e) => { if (e.target === e.currentTarget && !busy) onClose(); }}>
      <div className="dlg" role="dialog" aria-modal="true" aria-labelledby="dayDlgTitle">
        <header className="dlg-head">
          <h3 id="dayDlgTitle">{md(day)} ({dow(day)}) 예약</h3>
          <button type="button" className="btn-ghost" onClick={onClose} disabled={busy} aria-label="닫기">✕</button>
        </header>

        {toast && <p className="dlg-toast" role="status">{toast}</p>}
        {err && <p className="dlg-err" role="alert">{err}</p>}

        {events.length ? (
          <ul className="day-list">
            {events.map((ev) => (
              <li key={ev.key} className={panel?.ev?.key === ev.key ? 'is-open' : undefined}>
                <div className="day-row">
                  <b className="day-time">{khm(ev.slot)}</b>
                  <span className="day-main">
                    <span>{ev.label}{ev.kind === 'manual' && <span className="badge badge-setup">수기</span>}</span>
                    <small>{ev.who}{ev.kind === 'manual' && ev.m.memo ? ` · ${ev.m.memo}` : ''}</small>
                  </span>
                  <span className={`st-chip st-${ev.kind === 'manual' ? 'manual' : ev.status}`}>{ST[ev.status]}</span>
                </div>
                {ev.kind === 'db' && ev.req.message_translated && <p className="day-msg">환자 메시지: {ev.req.message_translated}</p>}
                <div className="day-acts">
                  {actionsFor(ev).map((a) => (
                    <button key={a.mode} type="button" className={a.mode === 'reject' || a.mode === 'no_show' ? 'btn-ghost is-danger' : 'btn-ghost'}
                      disabled={busy} onClick={() => { setErr(''); setToast(''); setPanel({ ev, mode: a.mode }); }}>{a.label}</button>
                  ))}
                </div>
                {panel?.ev?.key === ev.key && (
                  ev.kind === 'manual'
                    ? <ManualForm day={day} initial={ev.m} busy={busy} onCancel={() => setPanel(null)}
                        onSave={(m) => run(() => saveManual(m), '수기 예약을 고쳤어요 (이 브라우저에 저장)')}
                        onDelete={() => run(() => removeManual(ev.m.id), '수기 예약을 지웠어요')} />
                    : <ActionForm ev={ev} mode={panel.mode} day={day} busy={busy} onCancel={() => setPanel(null)} act={act} />
                )}
              </li>
            ))}
          </ul>
        ) : <p className="locked-when">이날 예약이 없어요</p>}

        {panel?.mode === 'manual' && !panel.ev ? (
          <ManualForm day={day} busy={busy} onCancel={() => setPanel(null)}
            onSave={(m) => run(() => saveManual(m), '수기 예약을 추가했어요 (이 브라우저에 저장)')} />
        ) : (
          <button type="button" className="btn day-add" disabled={busy} onClick={() => { setErr(''); setToast(''); setPanel({ mode: 'manual' }); }}>+ 수기 예약 추가</button>
        )}
        <p className="mini">확정·시간 제안·거절·방문 처리는 DB에 저장되고 환자 화면에 바로 반영돼요. 거절·미방문은 되돌릴 수 없어요</p>
      </div>
    </div>
  );
}

// DB 예약 처리 폼 (확정할 시간 고르기 · 제안할 시간 · 거절 사유 · 방문/미방문 확인)
function ActionForm({ ev, mode, day, busy, onCancel, act }: {
  ev: Ev & { kind: 'db' }; mode: NonNullable<Panel>['mode']; day: string; busy: boolean; onCancel: () => void;
  act: (ev: Ev & { kind: 'db' }, action: string, body: object, done: string) => Promise<void>;
}) {
  const [slot, setSlot] = useState(ev.req.preferred_slots[0] ?? '');
  const [d, setD] = useState(day < todayKst() ? todayKst() : day);
  const [t, setT] = useState('10:00');
  const [reason, setReason] = useState('');
  const [err, setErr] = useState('');

  const submit = () => {
    setErr('');
    if (mode === 'confirm') {
      if (!slot) return setErr('확정할 시간을 골라 주세요');
      return act(ev, 'confirm', { slot }, `예약을 확정했어요: ${slotLabel(slot)}`);
    }
    if (mode === 'propose') {
      const iso = toIso(d, t);
      if (new Date(iso) <= new Date()) return setErr('지난 시간은 고를 수 없어요');
      return act(ev, 'propose', { slot: iso }, `다른 시간을 제안했어요: ${slotLabel(iso)}`);
    }
    if (mode === 'reject') {
      if (!reason) return setErr('거절 사유를 골라 주세요');
      return act(ev, 'reject', { reason }, '요청을 거절했어요');
    }
    return act(ev, mode, {}, mode === 'visited' ? '방문 완료로 바꿨어요' : '미방문으로 바꿨어요');
  };

  return (
    <div className="day-panel">
      {mode === 'confirm' && (
        <fieldset>
          <legend>확정할 시간 (환자 희망)</legend>
          {ev.req.preferred_slots.map((s, i) => (
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
        <p className="note">확정 시간 {ev.req.confirmed_slot ? slotLabel(ev.req.confirmed_slot) : '—'} 예약을 {mode === 'visited' ? '방문 완료' : '미방문'}로 바꿀까요?{mode === 'no_show' && ' 되돌릴 수 없어요.'}</p>
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

// 수기 예약 추가·수정 폼
function ManualForm({ day, initial, busy, onCancel, onSave, onDelete }: {
  day: string; initial?: ManualBooking; busy: boolean; onCancel: () => void;
  onSave: (m: Omit<ManualBooking, 'id'> & { id?: string }) => void; onDelete?: () => void;
}) {
  const [t, setT] = useState(initial ? khm(initial.slot) : '10:00');
  const [name, setName] = useState(initial?.name ?? '');
  const [treatment, setTreatment] = useState(initial?.treatment ?? '');
  const [memo, setMemo] = useState(initial?.memo ?? '');
  const [status, setStatus] = useState<ManualStatus>(initial?.status ?? 'confirmed');
  const [err, setErr] = useState('');

  const submit = () => {
    if (!name.trim()) return setErr('환자 표시 이름을 입력해 주세요 (이니셜 권장)');
    onSave({ id: initial?.id, slot: toIso(day, t), name: name.trim(), treatment: treatment.trim(), memo: memo.trim(), status });
  };

  return (
    <div className="day-panel">
      <p className="day-panel-title">{initial ? '수기 예약 수정' : `${md(day)} 수기 예약 추가`}</p>
      <div className="form-grid">
        <label><span>시간</span><select value={t} onChange={(e) => setT(e.target.value)}>{TIMES.map((x) => <option key={x}>{x}</option>)}</select></label>
        <label><span>상태</span>
          <select value={status} onChange={(e) => setStatus(e.target.value as ManualStatus)}>
            {(['confirmed', 'visited', 'no_show', 'cancelled'] as const).map((s) => <option key={s} value={s}>{ST[s]}</option>)}
          </select>
        </label>
        <label><span>환자 표시 이름</span><input value={name} onChange={(e) => setName(e.target.value)} placeholder="예: L.W. (대만)" maxLength={30} /></label>
        <label><span>진료 항목</span><input value={treatment} onChange={(e) => setTreatment(e.target.value)} placeholder="예: 레이저 토닝" maxLength={30} /></label>
        <label className="span2"><span>메모</span><input value={memo} onChange={(e) => setMemo(e.target.value)} placeholder="예: 전화 접수, 통역 필요" maxLength={80} /></label>
      </div>
      <p className="mini">이 브라우저에만 저장돼요. 실명·연락처·건강정보는 넣지 마세요</p>
      {err && <p className="dlg-err">{err}</p>}
      <div className="day-acts">
        {onDelete && <button type="button" className="btn-ghost is-danger" onClick={onDelete} disabled={busy}>삭제</button>}
        <span style={{ flex: 1 }} />
        <button type="button" className="btn-ghost" onClick={onCancel} disabled={busy}>취소</button>
        <button type="button" className="btn" onClick={submit} disabled={busy}>{busy ? '저장 중…' : '저장'}</button>
      </div>
    </div>
  );
}
