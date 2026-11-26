// "진료·결제 확인" 탭. 옛 /dashboard/legacy 진료·결제 확인 화면을 새 디자인으로
// 백엔드에 결제 금액·영수증 기능이 아직 없어 전부 예시 (입력해도 이 화면에서만 바뀌고 저장 안 됨)
// 요금 v4: 기본 회원 무료 + 수수료 13% / 프리미엄 연 ₩1,800,000(월 ₩150,000) + 수수료 8% — 확인 완료된 진료비 기준 (금액은 가정값)
import { useState } from 'react';
import type { TabProps } from './props';
import { Card, Locked, fmt } from '../ui';

type Row = { id: string; day: string; item: string; amount: number | null; pay: string; file: string; patient: string; status: 'done' | 'checking' | 'waiting' };
const ROWS: Row[] = [
  { id: 'R-1031', day: '11/12', item: '레이저 토닝 5회', amount: 2400000, pay: '카드', file: '영수증.pdf', patient: '✔ 11/13', status: 'done' },
  { id: 'R-1029', day: '11/10', item: '여드름 흉터 치료', amount: 3800000, pay: '현금', file: '영수증.jpg', patient: '✔ 11/11', status: 'done' },
  { id: 'R-1033', day: '11/13', item: '보톡스 (이마)', amount: 1200000, pay: '카드', file: '영수증.pdf', patient: '✔ 11/14', status: 'done' },
  { id: 'R-1034', day: '11/14', item: '기미 치료 3회', amount: 1860000, pay: '카드', file: '영수증.pdf', patient: '대기', status: 'checking' },
  { id: 'R-1035', day: '11/15', item: '필러', amount: 1200000, pay: '현금', file: '영수증.jpg', patient: '대기', status: 'checking' },
  { id: 'R-1036', day: '11/14', item: '피부 상담', amount: null, pay: '—', file: '—', patient: '—', status: 'waiting' },
];
const ST = { done: ['확인 완료', 'st-visited'], checking: ['확인 중', 'st-proposed'], waiting: ['입력 대기', 'st-no_show'] } as const;
// 이번 달 확인 완료 진료비 (팀 기준: 21건 × 1건 73만 원)
const CONFIRMED = { revenue: 15330000, count: 21 };
const CHECKING = { revenue: 3060000, count: 2 };
const CAP = { type: '의원', pct: 30 }; // 외국인환자 유치 수수료율 상한 (의원 30% · 병원·종합병원 20% · 상급종합 15%)
const won = (n: number) => `₩${fmt(n)}`;
const short = (n: number) => `₩${(n / 1e6).toFixed(1)}M`;

export default function ReceiptTab({ mode }: TabProps) {
  const operating = mode === 'operating';
  const [tier, setTier] = useState<'basic' | 'premium'>('premium');
  const [rows, setRows] = useState(ROWS);
  const [edit, setEdit] = useState<Row | null>(null);
  const rate = tier === 'basic' ? 0.13 : 0.08;
  const pct = Math.round(rate * 100);
  const tierName = tier === 'basic' ? '기본' : '프리미엄';
  const commission = Math.round(CONFIRMED.revenue * rate);
  const fee = tier === 'basic' ? 0 : 150000;
  const ratio = ((commission + fee) / CONFIRMED.revenue) * 100;
  const waiting = rows.filter((r) => r.status === 'waiting').length;

  if (!operating) {
    return (
      <div className="grid">
        <Locked title="진료·결제 확인 (확인 완료 매출·확인 중·입력 대기·이의 제기)" when="방문 완료 환자가 생기면 결제 금액·영수증을 여기서 등록해요" />
        <ProcessCard />
      </div>
    );
  }

  return (
    <div className="grid">
      <section className="card card-wide">
        <header className="card-head">
          <span className="badge badge-example">예시</span>
          <h3>결제 확인 현황</h3>
          <div className="period-presets" role="group" aria-label="회원 등급">
            {(['basic', 'premium'] as const).map((t) => (
              <button key={t} type="button" aria-pressed={tier === t} onClick={() => setTier(t)}>{t === 'basic' ? '기본 13%' : '프리미엄 8%'}</button>
            ))}
          </div>
        </header>
        <div className="today-tiles">
          <div className="today-tile is-static"><span className="today-label">확인 완료 매출</span><span className="today-val">{short(CONFIRMED.revenue)}</span><span className="today-go">{CONFIRMED.count}건 · 수수료 {won(commission)}</span></div>
          <div className="today-tile is-static"><span className="today-label">확인 중</span><span className="today-val">{short(CHECKING.revenue)}</span><span className="today-go">{CHECKING.count}건 · 확인되면 다음 청구</span></div>
          <div className={`today-tile is-static${waiting ? ' is-alert' : ''}`}><span className="today-label">입력 대기</span><span className="today-val">{waiting}건</span><span className="today-go">{waiting ? '결제 금액·영수증 입력 필요' : '모두 입력함'}</span></div>
          <div className="today-tile is-static"><span className="today-label">환자 이의 제기</span><span className="today-val">0건</span><span className="today-go">금액이 다르면 운영자가 확인</span></div>
        </div>
      </section>

      <Card title={`방문 완료 건 — 최근 ${rows.length}건 (이번 달 전체 24건)`} kind="example" wide>
        <div className="tbl-scroll">
          <table className="tbl req-tbl">
            <thead><tr><th>요청</th><th>방문일</th><th>진료 항목</th><th className="r">결제 금액 (부가세 제외)</th><th>결제 수단</th><th>영수증</th><th>환자 확인</th><th>상태</th><th className="r">수수료 ({tierName} {pct}%)</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td><b>{r.id}</b></td><td>{r.day}</td><td>{r.item}</td>
                  <td className="r">{r.amount != null ? won(r.amount) : <span className="mini">입력 전</span>}</td>
                  <td>{r.pay}</td>
                  <td>
                    {r.status === 'done' ? r.file : (
                      <>{r.file !== '—' && <span>{r.file} </span>}<button type="button" className={r.status === 'waiting' ? 'btn' : 'btn-ghost'} onClick={() => setEdit(r)}>{r.status === 'waiting' ? '금액·영수증 입력' : '바꾸기'}</button></>
                    )}
                  </td>
                  <td>{r.patient}</td>
                  <td><span className={`st-chip ${ST[r.status][1]}`}>{ST[r.status][0]}</span></td>
                  <td className="r">{r.amount != null ? won(Math.round(r.amount * rate)) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mini">입력하면 이 화면에서만 바뀌어요 (예시 — 저장 안 됨). 결제 금액·영수증 기능은 백엔드 연결 전이에요</p>
      </Card>

      <div className="row3 row-2">
        <ProcessCard />
        <Card title="수수료 상한 점검" kind="example">
          <div className="cap-row"><span>이 병원 종별</span><b>{CAP.type}</b></div>
          <div className="cap-row"><span>고시 상한 (진료비 대비)</span><b>{CAP.pct}%</b></div>
          <div className="cap-row"><span>현재 적용률</span><b>{pct}% ({tierName})</b></div>
          <span className="share-track"><span className="share-fill" style={{ width: `${(pct / CAP.pct) * 100}%` }} /></span>
          <div className="cap-row"><span>회원비까지 합친 비율 (이번 달)</span><b>{ratio.toFixed(1)}%</b></div>
          <span className="share-track"><span className="share-fill" style={{ width: `${Math.min(100, (ratio / CAP.pct) * 100)}%` }} /></span>
          <p className="mini">막대 끝 = 상한 {CAP.pct}% · 상한: 의원 30% · 병원·종합병원 20% · 상급종합 15% 이하 (외국인환자 유치 수수료율 통합 고시). 통역·숙박 등 비의료서비스 대가는 상한 밖 · 금액은 가정값</p>
        </Card>
      </div>

      {edit && (
        <ReceiptDialog row={edit} rate={rate} onClose={() => setEdit(null)}
          onSave={(amount, pay, file) => {
            setRows((rs) => rs.map((x) => (x.id === edit.id ? { ...x, amount, pay, file, status: 'checking', patient: '대기' } : x)));
            setEdit(null);
          }} />
      )}
    </div>
  );
}

function ProcessCard() {
  return (
    <Card title="확인 절차" kind="setup">
      <ol className="rules">
        <li>병원: 방문 완료 처리 → 실제 결제 금액·결제 수단 입력, 영수증 올리기</li>
        <li>환자: 마이페이지에서 같은 금액·영수증 확인 (3일 지나면 자동 확인)</li>
        <li>금액이 다르면 환자가 &ldquo;이의 제기&rdquo; → 메디대구 운영자가 병원과 확인</li>
        <li>확인 완료된 진료비 완납 건만 체결 수수료 계산</li>
      </ol>
    </Card>
  );
}

function ReceiptDialog({ row, rate, onClose, onSave }: { row: Row; rate: number; onClose: () => void; onSave: (amount: number, pay: string, file: string) => void }) {
  const [amount, setAmount] = useState(row.amount ? String(row.amount) : '');
  const [pay, setPay] = useState(row.pay !== '—' ? row.pay : '카드');
  const [file, setFile] = useState(row.file !== '—' ? row.file : '');
  const [err, setErr] = useState('');
  const n = Number(amount.replace(/[^\d]/g, ''));
  const save = () => {
    if (!(n > 0)) return setErr('결제 금액을 입력해 주세요');
    onSave(n, pay, file || '—');
  };
  return (
    <div className="dlg-wrap" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="dlg" role="dialog" aria-modal="true" aria-label={`${row.id} 결제 금액·영수증`}>
        <header className="dlg-head">
          <h3>{row.id} 결제 금액·영수증</h3>
          <button type="button" className="btn-ghost" onClick={onClose} aria-label="닫기">✕</button>
        </header>
        <p className="mini">{row.day} 방문 · {row.item}</p>
        <div className="form-grid">
          <label><span>결제 금액 (원, 부가세 제외)</span><input inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="예: 730000" /></label>
          <label><span>결제 수단</span>
            <select value={pay} onChange={(e) => setPay(e.target.value)}>{['카드', '현금', '계좌이체'].map((p) => <option key={p}>{p}</option>)}</select>
          </label>
          <label className="span2"><span>영수증 (사진·PDF)</span>
            <input type="file" accept="image/*,application/pdf" onChange={(e) => setFile(e.target.files?.[0]?.name ?? '')} />
          </label>
        </div>
        {n > 0 && <p className="mini">수수료 예상: ₩{fmt(Math.round(n * rate))} ({Math.round(rate * 100)}%) · 환자가 금액을 확인하면 &ldquo;확인 완료&rdquo;</p>}
        {err && <p className="dlg-err">{err}</p>}
        <p className="mini">예시 화면이라 저장되지 않고, 파일도 올라가지 않아요 (이름만 표시)</p>
        <div className="day-acts">
          <button type="button" className="btn-ghost" onClick={onClose}>취소</button>
          <button type="button" className="btn" onClick={save}>저장</button>
        </div>
      </div>
    </div>
  );
}
