// 홈 "요청 → 체결 → 방문" 옆 카드 2개 (운영 후 모드). 옛 /dashboard/legacy 통계 탭에서 가져와 새 디자인으로
// 방문자(page_events)·플랫폼 전체 집계는 백엔드에 아직 없어서 예시값 (sample.ts)
import { DEPT_LABEL, type DeptKey } from './types';
import { DAILY_VISITORS, PLATFORM_SHARE } from './sample';
import { Card, fmt } from './ui';

// 방문자 수 — 이번 달(실선) vs 지난달(점선), 일별 꺾은선
export function VisitorsCard() {
  const { now, prev } = DAILY_VISITORS;
  const W = 320, H = 150, L = 30, R = 8, T = 10, B = 22;
  const n = Math.max(now.length, prev.length);
  const max = Math.ceil((Math.max(...now, ...prev) * 1.1) / 20) * 20; // 눈금이 0·절반·끝 깔끔한 수가 되게
  const px = (i: number) => L + (i * (W - L - R)) / Math.max(n - 1, 1);
  const py = (v: number) => T + (H - T - B) * (1 - v / max);
  const path = (vals: number[]) => vals.map((v, i) => `${i ? 'L' : 'M'}${px(i).toFixed(1)},${py(v).toFixed(1)}`).join(' ');
  const ticks = [0, max / 2, max];
  const days = [0, Math.floor((n - 1) / 2), n - 1];
  const sum = (a: number[]) => a.reduce((x, y) => x + y, 0);
  return (
    <Card title="방문자 수 — 이번 달 vs 지난달 (일별)" kind="example">
      <p className="trend-legend"><i className="lg-now" /> 이번 달 {fmt(sum(now))}명 <i className="lg-prev" /> 지난달 같은 기간 {fmt(sum(prev))}명</p>
      <svg className="trend" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="일별 방문자 이번 달과 지난달">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={L} x2={W - R} y1={py(t)} y2={py(t)} className="base" />
            <text x={L - 4} y={py(t) + 4} textAnchor="end" className="axis">{t}</text>
          </g>
        ))}
        <path d={path(prev)} className="prev" />
        <path d={path(now)} className="now" />
        {now.map((v, i) => <circle key={i} cx={px(i)} cy={py(v)} r={i === now.length - 1 ? 3.5 : 2} className="pt" />)}
        {days.map((d) => <text key={d} x={px(d)} y={H - 5} textAnchor={d === 0 ? 'start' : d === n - 1 ? 'end' : 'middle'} className="axis">{d + 1}일</text>)}
      </svg>
      <p className="mini">방문자는 하루마다 바뀌는 무작위 값으로 세요. 개인정보는 저장하지 않아요</p>
    </Card>
  );
}

// 메디대구 전체 이용자 중 우리 병원 (비율만)
export function PlatformShareCard({ dept }: { dept: DeptKey }) {
  return (
    <Card title="메디대구 전체 이용자 중 우리 병원" kind="example">
      <ul className="share">
        {PLATFORM_SHARE.map((s) => {
          const label = s.label.replace('같은 진료과', `같은 진료과(${DEPT_LABEL[dept]})`);
          return (
            <li key={s.label}>
              <span className="share-row"><span>{label}</span><b>{s.pct}%</b></span>
              <span className="share-track"><span className="share-fill" style={{ width: `${Math.min(s.pct * 4, 100)}%` }} /></span>
            </li>
          );
        })}
      </ul>
      <p className="mini">전체 대비 비율만 보여요. 다른 병원의 순위·숫자는 보여주지 않아요 · 막대 길이는 25% = 끝까지</p>
    </Card>
  );
}
