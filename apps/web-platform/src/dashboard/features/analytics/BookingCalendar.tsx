// 상담·예약 "예약 캘린더" (운영 후 모드). 옛 /dashboard/legacy 주 단위 캘린더를 월 단위로, 새 디자인으로
// - 환자 예약(DB): GET /tenant/booking-requests?status=… → 대기는 환자 희망 1순위 시간, 나머지는 확정 시간에 표시
// - 날짜를 누르면 팝업: 그날 예약 목록 + DB 예약 처리(확정·시간 제안·거절·방문 완료·미방문, POST /tenant/booking-requests/{id}/{action})
//   + 수기 예약 추가·수정·삭제 (manualBookings.ts, 지금은 이 브라우저에만 저장)
import { useCallback, useEffect, useMemo, useState } from 'react';
import { readStaffToken } from '../../../features/staff/staffSession';
import {
  ACTIONS, ActionForm, DB_STATUSES, Expired, ST, TIMES, WEEK, call, dow, errText, khm, kday, md, reqId, reqTitle, reqWho, runAction, todayKst, toIso,
  type ActionMode, type DbReq,
} from './bookingShared';
import { listManual, removeManual, saveManual, type ManualBooking, type ManualStatus } from './manualBookings';

type Ev =
  | { kind: 'db'; key: string; slot: string; status: string; label: string; who: string; req: DbReq }
  | { kind: 'manual'; key: string; slot: string; status: ManualStatus; label: string; who: string; m: ManualBooking };

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

function toEvents(db: DbReq[], manual: ManualBooking[]): Ev[] {
  const evs: Ev[] = [];
  for (const r of db) {
    const slot = r.status === 'pending' ? r.preferred_slots[0] : r.confirmed_slot;
    if (!slot) continue;
    evs.push({
      kind: 'db', key: r.id, slot, status: r.status, req: r,
      label: reqTitle(r),
      who: `${reqId(r)} · ${reqWho(r)}`,
    });
  }
  for (const m of manual) evs.push({ kind: 'manual', key: m.id, slot: m.slot, status: m.status, m, label: m.treatment || '수기 예약', who: m.name || '이름 없음' });
  return evs.sort((a, b) => a.slot.localeCompare(b.slot));
}

export default function BookingCalendar({ rev = 0, onExpired, onChanged }: { rev?: number; onExpired: () => void; onChanged?: () => void }) {
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

  useEffect(() => { if (readStaffToken()) load(); }, [load, rev]); // rev: 요청 목록·채팅에서 처리하면 다시 불러옴

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
type Panel = { ev?: Ev; mode: ActionMode | 'manual' } | null;

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
      setErr(errText(code));
      if (code === 'booking.invalid_transition' || code === 'not_found') await refresh();
    } finally {
      setBusy(false);
    }
  };
  const act = (req: DbReq, action: ActionMode, body: object, done: string) => run(() => runAction(req, action, body), done);

  const actionsFor = (ev: Ev): { mode: NonNullable<Panel>['mode']; label: string }[] =>
    ev.kind === 'manual' ? [{ mode: 'manual', label: '수정' }] : ACTIONS[ev.status] ?? [];

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
                    : <ActionForm req={ev.req} mode={panel.mode as ActionMode} day={day} busy={busy} onCancel={() => setPanel(null)} act={act} />
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
