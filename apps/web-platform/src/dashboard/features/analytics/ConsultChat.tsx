// 상담·예약 "상담 채팅" (운영 후 모드). 옛 /dashboard/legacy 상담 채팅을 새 디자인으로
// 왼쪽: 처리 중인 요청(대기·시간 제안함·확정) · 오른쪽: 요청서·답장·방문 전 질문을 시간순 + 처리 버튼 + 답장 보내기
// 답장: POST /tenant/booking-requests/{id}/replies — 환자에게 가는 글은 확인 단계를 한 번 더 거침 (직원 승인 = 발송, compliance)
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { readStaffToken } from '../../../features/staff/staffSession';
import {
  ACTIONS, ActionDialog, Expired, ST, call, errText, loadOpenRequests, reqId, reqTitle, reqWho, slotLabel,
  type ActionMode, type DbReq,
} from './bookingShared';

type Msg = { from: 'patient' | 'staff'; main: string; sub: string | null; at: string };

const isKo = (s: string | null) => !!s && /[가-힣]/.test(s);
const when = (iso: string) => new Date(iso).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
const lastAsk = (r: DbReq) => Math.max(0, ...(r.questions ?? []).map((x) => Date.parse(x.created_at)));
const lastReply = (r: DbReq) => Math.max(0, ...(r.replies ?? []).map((x) => Date.parse(x.sent_at)));
// 빨간 점: 대기 중인데 병원 답장이 없거나, 마지막 글이 환자 질문
const unread = (r: DbReq) => (r.status === 'pending' && !(r.replies ?? []).length) || lastAsk(r) > lastReply(r);
const sub = (r: DbReq) =>
  (r.status === 'proposed' && r.confirmed_slot ? `시간 제안함 ${slotLabel(r.confirmed_slot)}`
    : r.status === 'confirmed' && r.confirmed_slot ? `확정 ${slotLabel(r.confirmed_slot)}`
    : r.preferred_slots[0] ? `희망 ${slotLabel(r.preferred_slots[0])}` : ST[r.status])
  + (r.visa_needed ? ' · 예약확인서 필요' : '');

function messages(r: DbReq): Msg[] {
  const tr = (t: string | null, orig: string | null, missing = '(번역 전)') => t || (isKo(orig) ? null : missing);
  const first: Msg[] = r.message_original ? [{ from: 'patient', main: r.message_original, sub: tr(r.message_translated, r.message_original), at: r.created_at }] : [];
  const rest: Msg[] = [
    ...(r.replies ?? []).map((x) => ({ from: 'staff' as const, main: x.text_ko, sub: x.text_translated || '(번역 연결 전 — 환자에게 한국어 원문)', at: x.sent_at })),
    ...(r.questions ?? []).map((x) => ({ from: 'patient' as const, main: x.text_original, sub: tr(x.text_translated, x.text_original, '(번역 전 — 번역 동의 없음)'), at: x.created_at })),
  ].sort((a, b) => Date.parse(a.at) - Date.parse(b.at));
  return [...first, ...rest];
}

export default function ConsultChat({ rev, onExpired, onChanged }: { rev: number; onExpired: () => void; onChanged: () => void }) {
  const [list, setList] = useState<DbReq[] | null>(null);
  const [error, setError] = useState(false);
  const [sel, setSel] = useState<string | null>(null);
  const [text, setText] = useState('');
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<{ ok: boolean; msg: string } | null>(null);
  const [open, setOpen] = useState<ActionMode | null>(null);
  const box = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    try { setList(await loadOpenRequests()); setError(false); }
    catch (e) { if (e instanceof Expired) onExpired(); else setError(true); }
  }, [onExpired]);
  useEffect(() => { if (readStaffToken()) load(); }, [load, rev]);

  const cur = useMemo(() => list?.find((r) => r.id === sel) ?? list?.[0] ?? null, [list, sel]);
  const msgs = useMemo(() => (cur ? messages(cur) : []), [cur]);
  useEffect(() => { if (box.current) box.current.scrollTop = box.current.scrollHeight; }, [msgs]);

  const pick = (id: string) => { setSel(id); setText(''); setConfirming(false); setNote(null); };

  const send = async () => {
    if (!cur) return;
    setBusy(true); setNote(null);
    try {
      await call(`/tenant/booking-requests/${cur.id}/replies`, { method: 'POST', body: JSON.stringify({ text: text.trim() }) });
      setText(''); setConfirming(false);
      setNote({ ok: true, msg: '답장을 보냈어요 (DB 저장)' });
      await load();
    } catch (e) {
      if (e instanceof Expired) { onExpired(); return; }
      setNote({ ok: false, msg: '보내지 못했어요: ' + errText((e as Error).message) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card card-wide">
      <header className="card-head">
        <span className="badge badge-live">실제</span>
        <h3>상담 채팅</h3>
        <span className="mini">{list ? `대화 ${list.length}개 · 답할 것 ${list.filter(unread).length}개` : error ? '서버에서 불러오지 못했어요' : '불러오는 중…'}</span>
      </header>

      <div className="chat">
        <div className="chat-list" role="listbox" aria-label="상담 목록">
          {list?.length ? list.map((r) => (
            <button key={r.id} type="button" role="option" aria-selected={cur?.id === r.id}
              className={`chat-item${cur?.id === r.id ? ' is-on' : ''}`} onClick={() => pick(r.id)}>
              <span className="chat-item-top"><b>{reqId(r)} · {reqWho(r)}</b>{unread(r) && <i className="chat-dot" aria-label="답할 것 있음" />}</span>
              <span>{reqTitle(r)} <span className={`st-chip st-${r.status}`}>{ST[r.status]}</span></span>
              <small>{sub(r)}</small>
            </button>
          )) : <p className="mini chat-empty">{list ? '대화가 없어요' : '불러오는 중…'}</p>}
        </div>

        {cur ? (
          <div className="chat-thread">
            <div className="chat-head">
              <div>
                <b>{reqId(cur)} · {reqTitle(cur)}</b>
                <small>{reqWho(cur)} · {sub(cur)}</small>
              </div>
              <div className="day-acts">
                {(ACTIONS[cur.status] ?? []).map((a) => (
                  <button key={a.mode} type="button" className={a.mode === 'reject' || a.mode === 'no_show' ? 'btn-ghost is-danger' : a.mode === 'confirm' || a.mode === 'visited' ? 'btn' : 'btn-ghost'}
                    onClick={() => { setNote(null); setOpen(a.mode); }}>{a.label}</button>
                ))}
              </div>
            </div>
            <div className="chat-sum">
              <b>요약</b> {cur.message_translated || cur.message_original || '메시지 없음'}
              <span className="chat-chips">
                {[reqTitle(cur), `희망일 ${cur.preferred_slots.length}개`, cur.visa_needed ? '비자 서류' : '비자 불필요'].map((t) => <span key={t} className="chip">{t}</span>)}
              </span>
            </div>
            <div className="chat-msgs" ref={box}>
              {msgs.length ? msgs.map((m, i) => (
                <div key={i} className={`msg msg-${m.from}`}>
                  <p>{m.main}</p>
                  {m.sub && <small>{m.from === 'patient' ? `번역: ${m.sub}` : `환자에게 보이는 글: ${m.sub}`}</small>}
                  <time>{m.from === 'patient' ? '환자' : '병원'} · {when(m.at)}</time>
                </div>
              )) : <p className="mini">아직 주고받은 글이 없어요</p>}
            </div>
            {note && <p className={note.ok ? 'dlg-toast' : 'dlg-err'} role="status">{note.msg}</p>}
            {confirming ? (
              <div className="chat-confirm">
                <p><b>환자에게 보낼까요?</b></p>
                <p className="chat-confirm-text">{text.trim()}</p>
                <p className="mini">보내면 되돌릴 수 없어요. 번역은 서버가 해서 환자 언어로 보여요 (번역이 안 되면 한국어 원문)</p>
                <div className="day-acts">
                  <button type="button" className="btn-ghost" onClick={() => setConfirming(false)} disabled={busy}>고치기</button>
                  <button type="button" className="btn" onClick={send} disabled={busy}>{busy ? '보내는 중…' : '보내기'}</button>
                </div>
              </div>
            ) : (
              <form className="chat-input" onSubmit={(e) => { e.preventDefault(); if (text.trim()) setConfirming(true); }}>
                <textarea value={text} onChange={(e) => setText(e.target.value)} rows={2} maxLength={1000}
                  placeholder="한국어로 입력하면 환자 언어로 번역돼 보내져요" aria-label="답장"
                  onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && text.trim()) setConfirming(true); }} />
                <button type="submit" className="btn" disabled={!text.trim()}>보내기</button>
              </form>
            )}
          </div>
        ) : <div className="chat-thread"><p className="mini">왼쪽에서 상담을 골라 주세요</p></div>}
      </div>
      <p className="mini">AI는 시술 횟수·효과 같은 의료 판단을 하지 않아요. 환자에게 가는 글은 직원이 확인해야 발송되고, 예약 확정도 직원이 눌러야 돼요</p>

      {open && cur && (
        <ActionDialog req={cur} mode={open} onExpired={onExpired} onClose={() => { setOpen(null); load(); }}
          onDone={(msg) => { setOpen(null); if (msg) setNote({ ok: true, msg }); onChanged(); }} />
      )}
    </section>
  );
}
