// 월별 매출 추이 (진료·결제 확인 탭). 막대 = 확인 완료 매출(진료비, 부가세 제외) · 선 = 메디대구 수수료 · 막대 아래 = 결제 건수
// 수수료 = 그 달 확인 완료 진료비 × 요율 (회원비는 수수료에 섞지 않고 따로). 지금은 예시 데이터, 결제 확인 API 생기면 교체
// 차트 라이브러리 없이 SVG로 직접 (KpiTrends 와 같은 방식)
import { useState } from 'react';
import { fmt } from './ui';

export type MonthRow = { month: string; revenue: number; count: number; checking?: number };

const won = (n: number) => `₩${fmt(n)}`;
const m = (n: number) => (n >= 1e6 ? `${+(n / 1e6).toFixed(n >= 1e7 ? 0 : 1)}M` : n >= 1e3 ? `${Math.round(n / 1e3)}K` : String(n));
const label = (ym: string) => `${+ym.slice(5)}월`;
const full = (ym: string) => `${ym.slice(0, 4)}년 ${+ym.slice(5)}월`;
// 보기 좋은 축 최대값 (1·2·2.5·5 × 10^n)
function nice(v: number) {
  if (v <= 0) return 1;
  const p = 10 ** Math.floor(Math.log10(v));
  return ([1, 2, 2.5, 5, 10].find((s) => s * p >= v) ?? 10) * p;
}

export default function MonthlyRevenueChart({ rows, rate, monthlyFee }: { rows: MonthRow[]; rate: number; monthlyFee: number }) {
  const [span, setSpan] = useState<6 | 12>(12);
  const data = rows.slice(-span);
  const [sel, setSel] = useState<number | null>(null);
  const idx = sel != null && sel < data.length ? sel : data.length - 1;

  if (!data.length) return <p className="note">방문 완료 후 결제 금액을 입력하면 여기에 월별로 쌓여요</p>;

  const W = 720, H = 240, L = 48, R = 48, T = 14, B = 40;
  const maxRev = nice(Math.max(...data.map((d) => d.revenue + (d.checking ?? 0))));
  const maxCom = nice(maxRev * rate);
  const slot = (W - L - R) / data.length;
  const bw = Math.min(36, slot * 0.56);
  const x = (i: number) => L + slot * i + slot / 2;
  const yR = (v: number) => T + (H - T - B) * (1 - v / maxRev);
  const yC = (v: number) => T + (H - T - B) * (1 - v / maxCom);
  const ticks = [0, 0.25, 0.5, 0.75, 1];
  const line = data.map((d, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${yC(d.revenue * rate).toFixed(1)}`).join(' ');

  const cur = data[idx];
  const prev = data[idx - 1];
  const diff = prev && prev.revenue ? ((cur.revenue - prev.revenue) / prev.revenue) * 100 : null;
  const total = data.reduce((s, d) => s + d.revenue, 0);
  const totalCount = data.reduce((s, d) => s + d.count, 0);

  return (
    <div className="rev">
      <div className="rev-top">
        <div className="period-presets" role="group" aria-label="기간">
          {([6, 12] as const).map((n) => (
            <button key={n} type="button" aria-pressed={span === n} onClick={() => { setSpan(n); setSel(null); }}>최근 {n}개월</button>
          ))}
        </div>
        <p className="trend-legend"><i className="lg-bar" /> 확인 완료 매출 <i className="lg-chk" /> 확인 중 <i className="lg-com" /> 수수료 ({Math.round(rate * 100)}%)</p>
      </div>

      <svg className="rev-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`최근 ${data.length}개월 매출과 수수료 추이`} onMouseLeave={() => setSel(null)}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={L} x2={W - R} y1={yR(maxRev * t)} y2={yR(maxRev * t)} className={t ? 'grid' : 'base'} />
            <text x={L - 6} y={yR(maxRev * t) + 4} textAnchor="end" className="axis">{m(maxRev * t)}</text>
            <text x={W - R + 6} y={yC(maxCom * t) + 4} className="axis axis-com">{m(maxCom * t)}</text>
          </g>
        ))}
        {data.map((d, i) => (
          <g key={d.month} className={i === idx ? 'is-sel' : ''}>
            <rect x={x(i) - bw / 2} y={yR(d.revenue)} width={bw} height={yR(0) - yR(d.revenue)} rx={4} className="bar" />
            {d.checking ? <rect x={x(i) - bw / 2} y={yR(d.revenue + d.checking)} width={bw} height={yR(0) - yR(d.checking)} rx={4} className="bar-chk" /> : null}
            <text x={x(i)} y={H - B + 16} textAnchor="middle" className="axis">{label(d.month)}</text>
            <text x={x(i)} y={H - B + 30} textAnchor="middle" className="axis axis-n">{d.count}건</text>
          </g>
        ))}
        <path d={line} className="com" />
        {data.map((d, i) => <circle key={d.month} cx={x(i)} cy={yC(d.revenue * rate)} r={i === idx ? 4.5 : 3} className="com-pt" />)}
        {/* 마우스·키보드로 달 고르기 (칸 전체) */}
        {data.map((d, i) => (
          <rect key={d.month} x={L + slot * i} y={T} width={slot} height={H - T - B + 34} className="hit" tabIndex={0}
            aria-label={`${full(d.month)} 매출 ${won(d.revenue)} ${d.count}건`}
            onMouseEnter={() => setSel(i)} onFocus={() => setSel(i)} onClick={() => setSel(i)} />
        ))}
      </svg>

      <div className="rev-detail" aria-live="polite">
        <b>{full(cur.month)}</b>
        <span>매출 <b>{won(cur.revenue)}</b> · {cur.count}건</span>
        <span>객단가 {cur.count ? won(Math.round(cur.revenue / cur.count)) : '—'}</span>
        <span>수수료 <b>{won(Math.round(cur.revenue * rate))}</b></span>
        {monthlyFee > 0 && <span>회원비 {won(monthlyFee)}</span>}
        {cur.checking ? <span>확인 중 {won(cur.checking)}</span> : null}
        {diff != null && <span className={diff >= 0 ? 'up' : 'down'}>전월 대비 {diff >= 0 ? '+' : ''}{diff.toFixed(0)}%</span>}
      </div>

      <div className="today-tiles">
        <div className="today-tile is-static"><span className="today-label">최근 {data.length}개월 매출</span><span className="today-val">₩{m(total)}</span><span className="today-go">{totalCount}건</span></div>
        <div className="today-tile is-static"><span className="today-label">같은 기간 수수료</span><span className="today-val">₩{m(Math.round(total * rate))}</span><span className="today-go">{monthlyFee ? `회원비 별도 ${won(monthlyFee * data.length)}` : '회원비 없음 (기본 회원)'}</span></div>
        <div className="today-tile is-static"><span className="today-label">월평균 객단가</span><span className="today-val">₩{m(totalCount ? total / totalCount : 0)}</span><span className="today-go">확인 완료 건 기준</span></div>
      </div>
    </div>
  );
}
