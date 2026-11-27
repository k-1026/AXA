// 사후관리 "사후관리 채팅" (운영 후 모드). 옛 /dashboard/legacy 사후관리 채팅을 새 디자인으로 (상담 채팅과 같은 모양)
// - 목록: GET /tenant/aftercare · 대화 열기: GET /tenant/aftercare/{id} (열람 기록이 남으므로 직원이 고를 때만 엶 — 자동으로 열지 않음)
// - 답장: POST /tenant/aftercare/{id}/messages (확인 단계 후 발송) · 상태: PATCH /tenant/aftercare/{id} {status, tags}
import { useCallback, useEffect, useRef, useState } from 'react';
import { readStaffToken } from '../../../features/staff/staffSession';
import { Expired, LANG, NAT, TRT, call, errText, slotLabel, retryTranslations } from './bookingShared';
import { WaitBadge, WaitLegend, clinicMinutes, useClinicClock, waitLevel } from './waitTime';

type Status = 'new' | 'in_progress' | 'resolved';
type Thread = {
  id: string; status: Status; tags: string[]; summary: string | null; lang: string; nationality: string;
  treatment: string | null; visited_slot: string | null; last_message_at: string; last_message: string | null; unanswered: number;
};
type Attachment = { kind: string; name?: string; url?: string; thumb_url?: string };
type Message = { id: number; sender: string; text_original: string; text_translated: string | null; has_photo: boolean; attachments: Attachment[]; created_at: string };
type ThreadFull = Thread & { messages: Message[] };

const AC_ST: Record<Status, string> = { new: '새 문의', in_progress: '처리 중', resolved: '해결됨' };
const AC_CHIP: Record<Status, string> = { new: 'st-pending', in_progress: 'st-proposed', resolved: 'st-visited' };
const isKo = (s: string | null) => !!s && /[가-힣]/.test(s);
const when = (iso: string) => new Date(iso).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
const tid = (t: Thread) => `A-${t.id.slice(0, 4).toUpperCase()}`;
const who = (t: Thread) => `${NAT[t.nationality] || t.nationality} · ${LANG[t.lang] || t.lang}`;
const title = (t: Thread) => t.tags[0] || TRT[t.treatment ?? ''] || t.treatment || '사후관리';
const sub = (t: Thread) => `${AC_ST[t.status]}${t.visited_slot ? ` · 방문 ${slotLabel(t.visited_slot)}` : ''}`;
const https = (u?: string) => !!u && /^https:\/\//.test(u);

// 사후관리 목록에는 번역 동의 여부가 없어 한 문구로 (동의가 있으면 서버가 다시 번역함)
const TR_MISSING = '(번역 없음 — 다시 번역하는 중이거나 번역 동의 없음)';

export default function AftercareChat({ rev, onExpired, onChanged }: { rev: number; onExpired: () => void; onChanged: () => void }) {
  const [list, setList] = useState<Thread[] | null>(null);
  const [error, setError] = useState(false);
  const [sel, setSel] = useState<string | null>(null);
  const [thread, setThread] = useState<ThreadFull | null>(null);
  const [loadingThread, setLoadingThread] = useState(false);
  const [text, setText] = useState('');
  const [confirming, setConfirming] = useState(false);
  const [statusPanel, setStatusPanel] = useState<Status | null>(null);
  const [tags, setTags] = useState('');
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<{ ok: boolean; msg: string } | null>(null);
  const box = useRef<HTMLDivElement>(null);
  const { hours, now } = useClinicClock();
  // 대기 시작점: 연 대화는 마지막 병원 답장 뒤 첫 환자 글(정확), 안 연 대화는 목록의 마지막 글 시각(목록 API에 첫 미답 시각이 없어 근사 — 실제보다 짧게 보일 수 있음)
  const waitMin = (t: Thread) => {
    if (t.status === 'resolved' || t.unanswered <= 0) return null;
    let since = t.last_message_at;
    if (thread?.id === t.id) {
      const lastStaff = Math.max(0, ...thread.messages.filter((m) => m.sender !== 'patient').map((m) => Date.parse(m.created_at)));
      const first = thread.messages.find((m) => m.sender === 'patient' && Date.parse(m.created_at) > lastStaff);
      if (first) since = first.created_at;
    }
    return clinicMinutes(since, now, hours);
  };

  const fail = useCallback((e: unknown) => {
    if (e instanceof Expired) { onExpired(); return true; }
    return false;
  }, [onExpired]);

  const loadList = useCallback(async () => {
    try { setList(await call<Thread[]>('/tenant/aftercare')); setError(false); }
    catch (e) { if (!fail(e)) setError(true); }
  }, [fail]);
  useEffect(() => { if (readStaffToken()) loadList(); }, [loadList, rev]);

  const openThread = useCallback(async (id: string) => {
    setLoadingThread(true);
    try {
      const t = await call<ThreadFull>(`/tenant/aftercare/${id}`);
      setThread(t);
      // 번역이 빠진 글이 있으면 서버에 다시 번역을 맡기고(동의 있는 것만), 된 게 있으면 다시 불러옴 (11/27)
      const gap = t.messages.some((m) => !m.text_translated && !(m.sender === 'patient' && isKo(m.text_original)) && m.text_original !== '📷');
      if (gap && (await retryTranslations())) setThread(await call<ThreadFull>(`/tenant/aftercare/${id}`));
    }
    catch (e) { if (!fail(e)) setNote({ ok: false, msg: '대화를 열지 못했어요: ' + errText((e as Error).message) }); }
    finally { setLoadingThread(false); }
  }, [fail]);

  useEffect(() => { if (box.current) box.current.scrollTop = box.current.scrollHeight; }, [thread]);

  const pick = (id: string) => {
    setSel(id); setText(''); setConfirming(false); setStatusPanel(null); setNote(null); setThread(null);
    openThread(id);
  };

  const after = async (msg: string) => {
    setNote({ ok: true, msg });
    await Promise.all([loadList(), sel ? openThread(sel) : null]);
    onChanged();
  };

  const send = async () => {
    if (!sel) return;
    setBusy(true); setNote(null);
    try {
      await call(`/tenant/aftercare/${sel}/messages`, { method: 'POST', body: JSON.stringify({ text: text.trim() }) });
      setText(''); setConfirming(false);
      await after('답장을 보냈어요 (DB 저장)');
    } catch (e) {
      if (!fail(e)) setNote({ ok: false, msg: '보내지 못했어요: ' + errText((e as Error).message) });
    } finally { setBusy(false); }
  };

  const changeStatus = async () => {
    if (!sel || !statusPanel) return;
    setBusy(true); setNote(null);
    try {
      const body: { status: Status; tags?: string[] } = { status: statusPanel };
      if (statusPanel === 'resolved') body.tags = tags.split(',').map((t) => t.trim()).filter(Boolean);
      await call(`/tenant/aftercare/${sel}`, { method: 'PATCH', body: JSON.stringify(body) });
      setStatusPanel(null);
      await after(`${AC_ST[body.status]}(으)로 바꿨어요 (DB 저장)`);
    } catch (e) {
      if (!fail(e)) setNote({ ok: false, msg: '바꾸지 못했어요: ' + errText((e as Error).message) });
    } finally { setBusy(false); }
  };

  const cur = thread ?? list?.find((t) => t.id === sel) ?? null;

  return (
    <section className="card">
      <header className="card-head">
        <span className="badge badge-live">실제</span>
        <h3>사후관리 채팅</h3>
        <span className="mini">{list ? `대화 ${list.length}개 · 미답변 ${list.filter((t) => t.status !== 'resolved' && t.unanswered > 0).length}개` : error ? '서버에서 불러오지 못했어요' : '불러오는 중…'}</span>
      </header>
      <WaitLegend known={hours.known} />

      <div className="chat">
        <div className="chat-list" role="listbox" aria-label="사후관리 대화 목록">
          {list?.length ? list.map((t) => {
            const wm = waitMin(t);
            return (
            <button key={t.id} type="button" role="option" aria-selected={sel === t.id}
              className={`chat-item${sel === t.id ? ' is-on' : ''}${wm != null ? ` wait-edge-${waitLevel(wm)}` : ''}`} onClick={() => pick(t.id)}>
              <span className="chat-item-top"><b>{tid(t)} · {who(t)}</b>{wm != null && <WaitBadge min={wm} />}</span>
              <span>{title(t)} <span className={`st-chip ${AC_CHIP[t.status]}`}>{AC_ST[t.status]}</span></span>
              <small>{t.last_message ? t.last_message.slice(0, 40) : sub(t)}</small>
            </button>
            );
          }) : <p className="mini chat-empty">{list ? '사후관리 대화가 없어요' : '불러오는 중…'}</p>}
        </div>

        {cur ? (
          <div className="chat-thread">
            <div className="chat-head">
              <div>
                <b>{tid(cur)} · {title(cur)} {waitMin(cur) != null && <WaitBadge min={waitMin(cur)!} />}</b>
                <small>{who(cur)} · {sub(cur)}</small>
              </div>
              <div className="day-acts">
                {cur.status !== 'in_progress' && cur.status !== 'resolved' && (
                  <button type="button" className="btn-ghost" disabled={busy} onClick={() => { setNote(null); setStatusPanel('in_progress'); }}>처리 중</button>
                )}
                {cur.status !== 'resolved' && (
                  <button type="button" className="btn" disabled={busy} onClick={() => { setNote(null); setTags(cur.tags.join(', ')); setStatusPanel('resolved'); }}>해결됨</button>
                )}
              </div>
            </div>

            {statusPanel && (
              <div className="chat-confirm">
                <p><b>{statusPanel === 'resolved' ? '해결됨으로 바꿀까요?' : '처리 중으로 바꿀까요?'}</b></p>
                {statusPanel === 'resolved' ? (
                  <>
                    <label className="pick"><span>태그 (쉼표로 구분)</span>
                      <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="예: 붉은기, 재방문 일정" />
                    </label>
                    <p className="mini">태그는 통계·비슷한 문의 찾기에 쓰여요. 해결된 대화도 환자가 다시 글을 쓰면 새 문의로 열려요</p>
                  </>
                ) : <p className="mini">다른 직원에게 "누가 보고 있음"으로 보여요</p>}
                <div className="day-acts">
                  <button type="button" className="btn-ghost" onClick={() => setStatusPanel(null)} disabled={busy}>취소</button>
                  <button type="button" className="btn" onClick={changeStatus} disabled={busy}>{busy ? '처리 중…' : statusPanel === 'resolved' ? '해결됨' : '처리 중'}</button>
                </div>
              </div>
            )}

            <div className="chat-sum">
              <b>요약</b> {cur.summary || cur.last_message || '요약 없음'}
              <span className="chat-chips">{(cur.tags.length ? cur.tags : [TRT[cur.treatment ?? ''] || '태그 없음']).map((t) => <span key={t} className="chip">{t}</span>)}</span>
            </div>

            <div className="chat-msgs" ref={box}>
              {loadingThread ? <p className="mini">대화를 불러오는 중…</p>
                : thread?.messages.length ? thread.messages.map((m) => {
                  const patient = m.sender === 'patient';
                  const files = (m.attachments ?? []).filter((a) => https(a.url));
                  const tr = patient ? (m.text_translated || (isKo(m.text_original) ? null : TR_MISSING)) : (m.text_translated || TR_MISSING);
                  return (
                    <div key={m.id} className={`msg msg-${patient ? 'patient' : 'staff'}`}>
                      {!(m.text_original === '📷' && files.length) && <p>{m.text_original}</p>}
                      {files.length > 0 && (
                        <span className="msg-media">
                          {files.map((a, i) => a.kind === 'video'
                            ? <video key={i} src={a.url} controls preload="metadata" aria-label={a.name || '영상'} />
                            : <a key={i} href={a.url} target="_blank" rel="noopener noreferrer"><img src={https(a.thumb_url) ? a.thumb_url : a.url} alt={a.name || '사진'} loading="lazy" /></a>)}
                        </span>
                      )}
                      {!files.length && m.has_photo && <small>📷 사진 있음 (직원만 열람)</small>}
                      {tr && <small>{patient ? `번역: ${tr}` : `환자에게 보이는 글: ${tr}`}</small>}
                      <time>{patient ? '환자' : '병원'} · {when(m.created_at)}</time>
                    </div>
                  );
                }) : <p className="mini">{thread ? '아직 주고받은 글이 없어요' : ''}</p>}
            </div>

            {note && <p className={note.ok ? 'dlg-toast' : 'dlg-err'} role="status">{note.msg}</p>}
            {confirming ? (
              <div className="chat-confirm">
                <p><b>환자에게 보낼까요?</b></p>
                <p className="chat-confirm-text">{text.trim()}</p>
                <p className="mini">보내면 되돌릴 수 없어요. 사후 진료 판단은 의료진이 직접 해요</p>
                <div className="day-acts">
                  <button type="button" className="btn-ghost" onClick={() => setConfirming(false)} disabled={busy}>고치기</button>
                  <button type="button" className="btn" onClick={send} disabled={busy}>{busy ? '보내는 중…' : '보내기'}</button>
                </div>
              </div>
            ) : (
              <form className="chat-input" onSubmit={(e) => { e.preventDefault(); if (text.trim()) setConfirming(true); }}>
                <textarea value={text} onChange={(e) => setText(e.target.value)} rows={2} maxLength={1000} disabled={!thread}
                  placeholder="한국어로 입력하면 환자 언어로 번역돼 보내져요" aria-label="답장"
                  onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && text.trim()) setConfirming(true); }} />
                <button type="submit" className="btn" disabled={!text.trim() || !thread}>보내기</button>
              </form>
            )}
          </div>
        ) : (
          <div className="chat-thread chat-pick"><p className="mini">왼쪽에서 대화를 골라 주세요. 대화를 열면 열람 기록이 남아요</p></div>
        )}
      </div>
      <p className="mini">문의 원문·사진은 이 병원 직원만 보고 열람 기록이 남아요. 같은 주제가 3건 미만이면 통계에 대표 사례를 보여주지 않아요</p>
    </section>
  );
}
