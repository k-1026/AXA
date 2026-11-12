// 대시보드 공용 조각: 카드, 배지, 막대, 선 그래프, 단계 막대, 잠긴 지표
import type { ReactNode } from 'react';

export const fmt = (n: number) => Math.round(n).toLocaleString('ko-KR');
export const won = (n: number) => `${fmt(n)}원`;
// 표본이 적을 때 숨김 (팀 판단값: 5 미만)
export const SMALL = 5;
export const masked = (n: number) => (n < SMALL ? '5 미만' : fmt(n));

type Kind = 'public' | 'example' | 'setup';
const KIND_LABEL: Record<Kind, string> = { public: '공공', example: '예시', setup: '설정' };

export function Badge({ kind }: { kind: Kind }) {
  return <span className={`badge badge-${kind}`}>{KIND_LABEL[kind]}</span>;
}

export function Card({
  title, kind, source, children, wide, action,
}: {
  title: string; kind: Kind; source?: string; children: ReactNode; wide?: boolean; action?: ReactNode;
}) {
  return (
    <section className={`card${wide ? ' card-wide' : ''}`}>
      <header className="card-head">
        <Badge kind={kind} />
        <h3>{title}</h3>
        {action}
      </header>
      <div className="card-body">{children}</div>
      {source && <p className="card-source">출처: {source}</p>}
    </section>
  );
}

// 운영 데이터가 아직 없을 때 같은 자리에 보여주는 칸
export function Locked({ title, when, setup }: { title: string; when: string; setup?: string }) {
  return (
    <section className="card card-locked">
      <header className="card-head">
        <span className="badge badge-locked">집계 전</span>
        <h3>{title}</h3>
      </header>
      <p className="locked-when">{when}</p>
      {setup && <p className="locked-setup">먼저 할 일: {setup}</p>}
    </section>
  );
}

export function BarList({
  items, value = (x) => x.n, label = (x) => fmt(value(x)), highlight, max,
}: {
  items: { name: string; n?: number; [k: string]: unknown }[];
  value?: (x: any) => number;
  label?: (x: any) => string;
  highlight?: string;
  max?: number;
}) {
  const top = max ?? Math.max(...items.map(value), 1);
  return (
    <ul className="bars">
      {items.map((x) => (
        <li key={x.name} className={x.name === highlight ? 'is-hl' : undefined}>
          <span className="bar-name">{x.name}</span>
          <span className="bar-track"><span className="bar-fill" style={{ width: `${(value(x) / top) * 100}%` }} /></span>
          <span className="bar-val">{label(x)}</span>
        </li>
      ))}
    </ul>
  );
}

// 세로축 0부터 시작하는 단순 선 그래프 (SVG)
export function LineChart({
  points, height = 160, yLabel = fmt, dashedFrom,
}: {
  points: { x: string; y: number }[]; height?: number; yLabel?: (n: number) => string; dashedFrom?: number;
}) {
  const W = 640, H = height, L = 52, R = 12, T = 12, B = 26;
  const max = Math.max(...points.map((p) => p.y)) * 1.1 || 1;
  const step = (W - L - R) / Math.max(points.length - 1, 1);
  const px = (i: number) => L + i * step;
  const py = (v: number) => T + (H - T - B) * (1 - v / max);
  const ticks = [0, 0.5, 1].map((t) => max * t / 1.1);
  const path = (from: number, to: number) =>
    points.slice(from, to).map((p, i) => `${i ? 'L' : 'M'}${px(from + i)},${py(p.y)}`).join(' ');
  const cut = dashedFrom ?? points.length;
  const every = Math.ceil(points.length / 8);
  const last = points[points.length - 1];
  return (
    <svg className="line" viewBox={`0 0 ${W} ${H}`} role="img">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={L} x2={W - R} y1={py(t)} y2={py(t)} className="grid" />
          <text x={L - 6} y={py(t) + 4} textAnchor="end" className="axis">{yLabel(t)}</text>
        </g>
      ))}
      <path d={`${path(0, cut)} L${px(cut - 1)},${py(0)} L${px(0)},${py(0)} Z`} className="area" />
      <path d={path(0, cut)} className="stroke" />
      {cut < points.length && <path d={path(cut - 1, points.length)} className="stroke dashed" />}
      {points.map((p, i) => (i % every === 0 || i === points.length - 1) && (
        <text key={p.x} x={px(i)} y={H - 6} textAnchor="middle" className="axis">{p.x}</text>
      ))}
      <circle cx={px(points.length - 1)} cy={py(last.y)} r={4} className="dot" />
    </svg>
  );
}

export function Delta({ now, prev, lowerIsBetter, unit }: { now: number; prev: number; lowerIsBetter?: boolean; unit?: string }) {
  const diff = unit === '%' ? now - prev : prev ? ((now - prev) / prev) * 100 : 0;
  const good = lowerIsBetter ? diff < 0 : diff > 0;
  const text = unit === '%' ? `${diff > 0 ? '+' : ''}${diff.toFixed(0)}%p` : `${diff > 0 ? '+' : ''}${diff.toFixed(0)}%`;
  return <span className={`delta ${diff === 0 ? '' : good ? 'is-good' : 'is-bad'}`}>{diff > 0 ? '▲' : diff < 0 ? '▼' : '–'} {text}</span>;
}

export function Funnel({ steps }: { steps: { name: string; n: number }[] }) {
  return (
    <ol className="funnel">
      {steps.map((s, i) => {
        const prev = i ? steps[i - 1].n : s.n;
        const rate = i ? Math.round((s.n / prev) * 100) : 100;
        return (
          <li key={s.name}>
            <span className="funnel-name">{s.name}</span>
            <span className="funnel-track"><span className="funnel-fill" style={{ width: `${Math.max((s.n / steps[0].n) * 100, 2)}%` }} /></span>
            <span className="funnel-n">{fmt(s.n)}</span>
            <span className={`funnel-rate${i && rate < 60 ? ' is-low' : ''}`}>{i ? `${rate}%` : ''}</span>
          </li>
        );
      })}
    </ol>
  );
}
