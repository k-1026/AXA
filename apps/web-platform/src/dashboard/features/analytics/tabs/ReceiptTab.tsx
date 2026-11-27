// "진료·결제 확인" 탭. 실제 DB (11/27): 방문 완료(visited) = 결제 금액 입력 대기, 결제 확인(paid) = 금액·수단 입력함
// GET /tenant/booking-requests?status=visited·paid, 입력은 POST /tenant/booking-requests/{id}/paid {amount, method} (contracts 2절)
// 회원 등급은 마이 병원에서 정한 값(membership.ts) · 요금 v4: 기본 회원 무료 + 수수료 13% / 프리미엄 연 ₩1,800,000(월 ₩150,000) + 수수료 8% — 결제 확인된 진료비 기준 (금액은 가정값)
// 환자 금액 확인·이의 제기·영수증 파일은 다음 단계 (아래 확인 절차에 표시)
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { TabProps } from './props';
import { Card, Locked, fmt } from '../ui';
import { useTier } from '../membership';
import { Expired, call, errText, kday, reqId, reqTitle, reqWho, todayKst, type DbReq } from '../bookingShared';
import { useStaffExpired } from '../useStaffExpired';
import { useAutoRefresh } from '../autoRefresh';
import MonthlyRevenueChart from '../MonthlyRevenueChart';
import { MONTHLY_REVENUE } from '../sample';

const METHODS = { card: '카드', cash: '현금', transfer: '계좌이체', other: '기타' } as const;
type Method = keyof typeof METHODS;
const CAP = { type: '의원', pct: 30 }; // 외국인환자 유치 수수료율 상한 (의원 30% · 병원·종합병원 20% · 상급종합 15%)
const won = (n: number) => `₩${fmt(n)}`;
const short = (n: number) => (n >= 1e6 ? `₩${(n / 1e6).toFixed(1)}M` : won(n));
const visitDay = (r: DbReq) => (r.confirmed_slot ? kday(r.confirmed_slot) : '');
const mdShort = (d: string) => (d ? `${+d.slice(5, 7)}/${+d.slice(8)}` : '—');

export default function ReceiptTab({ mode }: TabProps) {
  const operating = mode === 'operating';
  const tier = useTier(); // 회원 등급은 "마이 병원"에서 바꿈
  const onExpired = useStaffExpired();
  const auto = useAutoRefresh();
  const [rows, setRows] = useState<DbReq[] | null>(null);
  const [error, setError] = useState('');
  const [rev, setRev] = useState(0);
  const [edit, setEdit] = useState<DbReq | null>(null);
  const rate = tier === 'basic' ? 0.13 : 0.08;
  const pct = Math.round(rate * 100);
  const tierName = tier === 'basic' ? '기본' : '프리미엄';

  const load = useCallback(async () => {
    try {
      const [v, p] = await Promise.all([call<DbReq[]>('/tenant/booking-requests?status=visited'), call<DbReq[]>('/tenant/booking-requests?status=paid')]);
      setRows([...v, ...p].sort((a, b) => visitDay(b).localeCompare(visitDay(a))));
      setError('');
    } catch (e) {
      if (e instanceof Expired) onExpired(); else setError('서버에서 불러오지 못했어요');
    }
  }, [onExpired]);
  useEffect(() => { if (operating) void load(); }, [operating, load, rev, auto]);

  // 이번 달(방문일 기준) 결제 확인 합계
  const month = todayKst().slice(0, 7);
  const stats = useMemo(() => {
    const paid = (rows ?? []).filter((r) => r.status === 'paid' && r.paid_amount);
    const thisMonth = paid.filter((r) => visitDay(r).startsWith(month));
    const revenue = thisMonth.reduce((n, r) => n + (r.paid_amount ?? 0), 0);
    return { revenue, count: thisMonth.length, all: paid.length, waiting: (rows ?? []).filter((r) => r.status === 'visited').length };
  }, [rows, month]);
  const commission = Math.round(stats.revenue * rate);
  const fee = tier === 'basic' ? 0 : 150000;
  const ratio = stats.revenue ? ((commission + fee) / stats.revenue) * 100 : 0;

  if (!operating) {
    return (
      <div className="grid">
        <Locked title="진료·결제 확인 (결제 확인 매출·입력 대기·수수료)" when="방문 완료 환자가 생기면 결제 금액을 여기서 입력해요" />
        <ProcessCard />
      </div>
    );
  }

  return (
    <div className="grid">
      <section className="card card-wide">
        <header className="card-head">
          <span className="badge badge-live">실제</span>
          <h3>결제 확인 현황</h3>
          <a className="mini" href="#myhospital">{tierName} 회원 · 수수료 {pct}% (마이 병원에서 변경)</a>
          {error && <span className="today-err">{error}</span>}
        </header>
        <div className="today-tiles">
          <div className="today-tile is-static"><span className="today-label">이번 달 결제 확인 진료비</span><span className="today-val">{rows ? short(stats.revenue) : '…'}</span><span className="today-go">{stats.count}건 (방문일 기준)</span></div>
          <div className="today-tile is-static"><span className="today-label">이번 달 수수료</span><span className="today-val">{rows ? won(commission) : '…'}</span><span className="today-go">{tierName} {pct}% · 결제 확인된 진료비 × 요율</span></div>
          <div className={`today-tile is-static${stats.waiting ? ' is-alert' : ''}`}><span className="today-label">입력 대기</span><span className="today-val">{rows ? `${stats.waiting}건` : '…'}</span><span className="today-go">{stats.waiting ? '방문 완료 → 결제 금액 입력 필요' : '모두 입력함'}</span></div>
          <div className="today-tile is-static"><span className="today-label">결제 확인 (전체)</span><span className="today-val">{rows ? `${stats.all}건` : '…'}</span><span className="today-go">환자 금액 확인·이의 제기는 다음 단계</span></div>
        </div>
      </section>

      <Card title="월별 매출 추이" kind="example" wide>
        <MonthlyRevenueChart rows={MONTHLY_REVENUE} rate={rate} monthlyFee={fee} />
        <p className="mini">수수료 = 확인 완료 진료비 × {tierName} 요율 {pct}% · 예시 데이터 (월별 실제 값 연결은 다음 단계)</p>
      </Card>

      <Card title={`방문 완료·결제 확인 — ${rows?.length ?? 0}건`} kind="live" wide>
        <div className="tbl-scroll">
          <table className="tbl req-tbl">
            <thead><tr><th>요청</th><th>환자</th><th>방문일</th><th>진료 항목</th><th className="r">결제 금액 (부가세 제외)</th><th>결제 수단</th><th>상태</th><th className="r">수수료 ({tierName} {pct}%)</th></tr></thead>
            <tbody>
              {(rows ?? []).map((r) => (
                <tr key={r.id}>
                  <td><b>{reqId(r)}</b></td><td>{reqWho(r)}</td><td>{mdShort(visitDay(r))}</td><td>{reqTitle(r)}</td>
                  <td className="r">{r.paid_amount != null ? won(r.paid_amount) : <button type="button" className="btn" onClick={() => setEdit(r)}>금액 입력</button>}</td>
                  <td>{r.paid_method ? METHODS[r.paid_method as Method] ?? r.paid_method : '—'}</td>
                  <td><span className={`st-chip st-${r.status}`}>{r.status === 'paid' ? '결제 확인' : '입력 대기'}</span></td>
                  <td className="r">{r.paid_amount != null ? won(Math.round(r.paid_amount * rate)) : '—'}</td>
                </tr>
              ))}
              {rows && !rows.length && <tr><td colSpan={8} className="mini">아직 방문 완료된 예약이 없어요. 상담·예약 탭에서 확정 예약을 &ldquo;방문 완료&rdquo;로 바꾸면 여기에 나와요</td></tr>}
            </tbody>
          </table>
        </div>
        <p className="mini">금액을 넣으면 &ldquo;결제 확인&rdquo;으로 바뀌어요 (고치기는 다음 단계 — 운영자에게 연락)</p>
      </Card>

      <div className="row3 row-2">
        <ProcessCard />
        <Card title="수수료 상한 점검" kind="live">
          <div className="cap-row"><span>이 병원 종별</span><b>{CAP.type}</b></div>
          <div className="cap-row"><span>고시 상한 (진료비 대비)</span><b>{CAP.pct}%</b></div>
          <div className="cap-row"><span>현재 적용률</span><b>{pct}% ({tierName})</b></div>
          <span className="share-track"><span className="share-fill" style={{ width: `${(pct / CAP.pct) * 100}%` }} /></span>
          <div className="cap-row"><span>회원비까지 합친 비율 (이번 달)</span><b>{stats.revenue ? `${ratio.toFixed(1)}%` : '—'}</b></div>
          <span className="share-track"><span className="share-fill" style={{ width: `${Math.min(100, (ratio / CAP.pct) * 100)}%` }} /></span>
          <p className="mini">막대 끝 = 상한 {CAP.pct}% · 상한: 의원 30% · 병원·종합병원 20% · 상급종합 15% 이하 (외국인환자 유치 수수료율 통합 고시). 통역·숙박 등 비의료서비스 대가는 상한 밖 · 요율·회원비는 가정값</p>
        </Card>
      </div>

      {edit && (
        <PaidDialog req={edit} rate={rate} onClose={() => setEdit(null)} onExpired={onExpired}
          onSaved={() => { setEdit(null); setRev((n) => n + 1); }} />
      )}
    </div>
  );
}

function ProcessCard() {
  return (
    <Card title="확인 절차" kind="setup">
      <ol className="rules">
        <li>병원: 상담·예약 탭에서 &ldquo;방문 완료&rdquo; → 여기서 실제 결제 금액·결제 수단 입력 → &ldquo;결제 확인&rdquo;</li>
        <li>결제 확인된 진료비 × 회원 등급 요율 = 체결 수수료</li>
        <li>다음 단계: 영수증 올리기 · 환자가 마이페이지에서 금액 확인(3일 지나면 자동) · 금액이 다르면 &ldquo;이의 제기&rdquo; → 운영자 확인</li>
      </ol>
    </Card>
  );
}

function PaidDialog({ req, rate, onClose, onSaved, onExpired }: { req: DbReq; rate: number; onClose: () => void; onSaved: () => void; onExpired: () => void }) {
  const [amount, setAmount] = useState('');
  const [method, setMethod] = useState<Method>('card');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const n = Number(amount.replace(/[^\d]/g, ''));
  const save = async () => {
    if (!(n > 0)) return setErr('결제 금액을 입력해 주세요');
    setBusy(true);
    setErr('');
    try {
      await call(`/tenant/booking-requests/${req.id}/paid`, { method: 'POST', body: JSON.stringify({ amount: n, method }) });
      onSaved();
    } catch (e) {
      if (e instanceof Expired) onExpired(); else setErr(errText((e as Error).message));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="dlg-wrap" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="dlg" role="dialog" aria-modal="true" aria-label={`${reqId(req)} 결제 금액`}>
        <header className="dlg-head">
          <h3>{reqId(req)} 결제 금액</h3>
          <button type="button" className="btn-ghost" onClick={onClose} aria-label="닫기">✕</button>
        </header>
        <p className="mini">{mdShort(visitDay(req))} 방문 · {reqTitle(req)} · {reqWho(req)}</p>
        <div className="form-grid">
          <label><span>결제 금액 (원, 부가세 제외)</span><input inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="예: 730000" autoFocus /></label>
          <label><span>결제 수단</span>
            <select value={method} onChange={(e) => setMethod(e.target.value as Method)}>
              {(Object.keys(METHODS) as Method[]).map((m) => <option key={m} value={m}>{METHODS[m]}</option>)}
            </select>
          </label>
        </div>
        {n > 0 && <p className="mini">{won(n)} · 수수료 예상 {won(Math.round(n * rate))} ({Math.round(rate * 100)}%)</p>}
        {err && <p className="dlg-err">{err}</p>}
        <div className="day-acts">
          <button type="button" className="btn-ghost" onClick={onClose}>취소</button>
          <button type="button" className="btn" onClick={save} disabled={busy}>{busy ? '저장 중…' : '결제 확인'}</button>
        </div>
      </div>
    </div>
  );
}
