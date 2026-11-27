// 홈 "기간 성과" (운영 후 모드). 사용자가 기간을 고르고, 지표마다 이번 기간(실선)·직전 같은 길이 기간(점선) 그래프
// 숫자는 실제 DB: GET /tenant/analytics/summary?from&to (기간 합계만 줌) → 기간을 최대 12구간으로 나눠 구간마다 불러 선을 그림
// 나중에 백엔드가 날짜별 숫자(series)를 주면 loadBuckets만 바꾸면 됨
// 11/27: 합계(1번)를 먼저 받아 숫자부터 보여 주고, 그래프 구간(최대 24번)은 그 뒤 다른 카드 요청보다 뒤에 (staffGet 줄 맨 뒤)
import { useEffect, useMemo, useState } from 'react';
import { readStaffToken } from '../../../features/staff/staffSession';
import { fmt } from './ui';
import { staffGet } from './staffGet';

type KpiKey = 'views' | 'requests' | 'confirmed' | 'visited' | 'cancelRate';
type Kpi = { key: KpiKey; now: number | null; prev: number | null; unit: 'count' | 'percent'; lowerIsBetter?: boolean };
export type Summary = { period: { from: string; to: string; prevFrom: string; prevTo: string }; kpi: Kpi[]; funnel: { key: 'requests' | 'confirmed' | 'visited'; n: number }[] };
type Bucket = { label: string; now: Record<KpiKey, number | null>; prev: Record<KpiKey, number | null> };
type Trends = { summary: Summary; buckets: Bucket[]; size: number };

const META: { key: KpiKey; label: string; unit: string }[] = [
  { key: 'views', label: '상세페이지 방문자', unit: '명' },
  { key: 'requests', label: '상담 신청', unit: '건' },
  { key: 'confirmed', label: '예약 확정', unit: '건' },
  { key: 'visited', label: '방문 완료', unit: '건' },
  { key: 'cancelRate', label: '취소율', unit: '%' },
];
const MAX_BUCKETS = 12;
const MAX_DAYS = 366;

// ---------- 날짜 (브라우저 시간 = 한국 기준으로 사용) ----------
const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const parse = (s: string) => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };
const addDays = (s: string, n: number) => { const d = parse(s); d.setDate(d.getDate() + n); return iso(d); };
const daysBetween = (a: string, b: string) => Math.round((parse(b).getTime() - parse(a).getTime()) / 86400000) + 1;
const md = (s: string) => `${Number(s.slice(5, 7))}/${Number(s.slice(8))}`;

const PRESETS = [
  { key: 'month', label: '이번 달', range: (t: string) => [t.slice(0, 8) + '01', t] },
  { key: '7d', label: '지난 7일', range: (t: string) => [addDays(t, -6), t] },
  { key: '30d', label: '지난 30일', range: (t: string) => [addDays(t, -29), t] },
  { key: '90d', label: '지난 3개월', range: (t: string) => [addDays(t, -89), t] },
] as const;

class Expired extends Error {}

const summaryPath = (from: string, to: string) => `/tenant/analytics/summary?from=${from}&to=${to}`;
// 이번 달 1일~오늘 — "이번 달"(처음 값)과 같은 주소. 홈 "오늘 할 일"도 이 주소를 써서 한 번만 부름
export const monthSummaryPath = () => { const t = iso(new Date()); return summaryPath(t.slice(0, 8) + '01', t); };

async function getSummary(from: string, to: string, first = true): Promise<Summary> {
  const res = await staffGet(summaryPath(from, to), { first });
  if (res.status === 401) throw new Expired();
  if (!res.ok) throw new Error(String(res.status));
  return res.body as Summary;
}

const toRecord = (s: Summary) => Object.fromEntries(s.kpi.map((k) => [k.key, k.now])) as Record<KpiKey, number | null>;

async function loadBuckets(from: string, to: string): Promise<Pick<Trends, 'buckets' | 'size'>> {
  const days = daysBetween(from, to);
  const size = Math.ceil(days / MAX_BUCKETS); // 구간 하나의 날 수
  const starts: number[] = [];
  for (let i = 0; i < days; i += size) starts.push(i);
  const range = (base: string, i: number) => [addDays(base, i), addDays(base, Math.min(i + size, days) - 1)] as const;
  const prevFrom = addDays(from, -days);
  const [nowParts, prevParts] = await Promise.all([
    Promise.all(starts.map((i) => getSummary(...range(from, i), false))),
    Promise.all(starts.map((i) => getSummary(...range(prevFrom, i), false))),
  ]);
  const buckets = starts.map((i, n) => ({
    label: md(range(from, i)[0]),
    now: toRecord(nowParts[n]),
    prev: toRecord(prevParts[n]),
  }));
  return { buckets, size };
}

// ---------- 이번 기간·지난 기간 겹친 선 그래프 (값 없음 = 끊김) ----------
function CompareChart({ buckets, k }: { buckets: Bucket[]; k: KpiKey }) {
  const W = 300, H = 96, L = 6, R = 6, T = 8, B = 18;
  const now = buckets.map((b) => b.now[k]);
  const prev = buckets.map((b) => b.prev[k]);
  const max = Math.max(1, ...now.map((v) => v ?? 0), ...prev.map((v) => v ?? 0)) * 1.15;
  const step = (W - L - R) / Math.max(buckets.length - 1, 1);
  const px = (i: number) => (buckets.length === 1 ? W / 2 : L + i * step);
  const py = (v: number) => T + (H - T - B) * (1 - v / max);
  const path = (vals: (number | null)[]) => {
    let d = '', pen = false;
    vals.forEach((v, i) => {
      if (v == null) { pen = false; return; }
      d += `${pen ? 'L' : 'M'}${px(i).toFixed(1)},${py(v).toFixed(1)} `;
      pen = true;
    });
    return d.trim();
  };
  const lastIdx = now.reduce<number>((acc, v, i) => (v == null ? acc : i), -1);
  const first = buckets[0]?.label, last = buckets[buckets.length - 1]?.label;
  return (
    <svg className="trend" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="이번 기간과 지난 기간 추이">
      <line x1={L} x2={W - R} y1={py(0)} y2={py(0)} className="base" />
      <path d={path(prev)} className="prev" />
      <path d={path(now)} className="now" />
      {now.map((v, i) => v != null && buckets.length <= 12 && <circle key={i} cx={px(i)} cy={py(v)} r={i === lastIdx ? 3.5 : 2} className="pt" />)}
      <text x={L} y={H - 4} className="axis">{first}</text>
      {last !== first && <text x={W - R} y={H - 4} textAnchor="end" className="axis">{last}</text>}
    </svg>
  );
}

const show = (v: number | null, unit: string) => (v == null ? '—' : `${fmt(v)}${unit}`);

// onSummary: 고른 기간의 합계를 홈의 다른 카드(요청 → 체결 → 방문)에도 넘김
export default function KpiTrends({ onExpired, onSummary }: { onExpired: () => void; onSummary?: (s: Summary | null) => void }) {
  const today = useMemo(() => iso(new Date()), []);
  const [preset, setPreset] = useState<string>('month');
  const [range, setRange] = useState<[string, string]>(() => PRESETS[0].range(today) as [string, string]);
  const [data, setData] = useState<Trends | null>(null);
  const [state, setState] = useState<'loading' | 'ok' | 'error'>('loading');
  const [from, to] = range;
  const invalid = from > to ? '시작일이 종료일보다 늦어요' : to > today ? '오늘 이후는 고를 수 없어요' : daysBetween(from, to) > MAX_DAYS ? '기간은 1년까지 고를 수 있어요' : '';

  useEffect(() => {
    const token = readStaffToken();
    if (!token || invalid) return;
    let alive = true;
    setState('loading');
    onSummary?.(null);
    getSummary(from, to)
      .then(async (summary) => {
        if (!alive) return;
        setData({ summary, buckets: [], size: 0 }); // 숫자 먼저
        setState('ok');
        onSummary?.(summary);
        const b = await loadBuckets(from, to);
        if (alive) setData({ summary, ...b });
      })
      .catch((e) => { if (!alive) return; if (e instanceof Expired) onExpired(); else setState('error'); });
    return () => { alive = false; };
  }, [from, to, invalid, onExpired, onSummary]);

  const pick = (key: string) => {
    const p = PRESETS.find((x) => x.key === key)!;
    setPreset(key);
    setRange(p.range(today) as [string, string]);
  };
  const setDate = (i: 0 | 1, v: string) => {
    if (!v) return;
    setPreset('custom');
    setRange((r) => (i === 0 ? [v, r[1]] : [r[0], v]));
  };

  const p = data?.summary.period;
  const kpi = (k: KpiKey) => data?.summary.kpi.find((x) => x.key === k);

  return (
    <section className="card card-wide">
      <header className="card-head">
        <span className="badge badge-live">실제</span>
        <h3>기간 성과 (직전 같은 기간 대비)</h3>
      </header>

      <div className="period">
        <div className="period-presets" role="group" aria-label="기간 빠른 선택">
          {PRESETS.map((x) => (
            <button key={x.key} type="button" aria-pressed={preset === x.key} onClick={() => pick(x.key)}>{x.label}</button>
          ))}
        </div>
        <div className="period-dates">
          <input type="date" aria-label="시작일" value={from} max={today} onChange={(e) => setDate(0, e.target.value)} />
          <span>~</span>
          <input type="date" aria-label="종료일" value={to} max={today} onChange={(e) => setDate(1, e.target.value)} />
        </div>
        <p className="period-note">
          {invalid ? <span className="period-err">{invalid}</span>
            : p ? <>이번 기간 {md(p.from)}~{md(p.to)} · 비교 {md(p.prevFrom)}~{md(p.prevTo)}{data && data.size > 1 && ` · 그래프 한 점 = ${data.size}일`}{data && !data.size && ' · 그래프 불러오는 중…'}</>
            : '불러오는 중…'}
          {state === 'error' && !invalid && <span className="period-err"> · 서버에서 불러오지 못했어요</span>}
        </p>
      </div>

      <p className="trend-legend"><i className="lg-now" /> 이번 기간 <i className="lg-prev" /> 지난 기간</p>

      <div className={`trends${state === 'loading' ? ' is-loading' : ''}`}>
        {META.map((m) => {
          const k = kpi(m.key);
          const pending = data && k && k.now == null && m.key === 'views';
          return (
            <div className="trend-card" key={m.key}>
              <span className="kpi-label">{m.label}</span>
              {pending ? (
                <>
                  <span className="kpi-val">집계 전</span>
                  <span className="trend-sub">방문 기록이 쌓이면 채워져요</span>
                </>
              ) : (
                <>
                  <span className="kpi-val">{data ? show(k?.now ?? null, m.unit) : '…'}</span>
                  <span className="trend-sub">지난 기간 {data ? show(k?.prev ?? null, m.unit) : '…'}</span>
                  {data && data.buckets.length > 0 && <CompareChart buckets={data.buckets} k={m.key} />}
                </>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
