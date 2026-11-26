// 홈 "요청 → 체결 → 방문" (운영 후 모드). 옛 /dashboard/legacy 상담·예약 탭의 박스를 새 디자인으로
// 숫자는 위 "기간 성과"에서 고른 기간의 실제 DB 합계 (GET /tenant/analytics/summary 의 funnel)
// 병원 페이지 조회(page_events)·시간 제안은 백엔드 집계 전이라 뺌
import type { Summary } from './KpiTrends';
import { Funnel } from './ui';

const NAME = { requests: '상담 요청', confirmed: '예약 체결', visited: '방문 완료' } as const;
const md = (s: string) => `${Number(s.slice(5, 7))}/${Number(s.slice(8))}`;

export default function FunnelCard({ summary }: { summary: Summary | null }) {
  const steps = summary?.funnel.map((f) => ({ name: NAME[f.key], n: f.n })) ?? [];
  const empty = summary && !steps[0]?.n;
  return (
    <section className="card card-live">
      <header className="card-head">
        <span className="badge badge-live">실제</span>
        <h3>요청 → 체결 → 방문</h3>
      </header>
      <div className="card-body">
        {!summary ? <p className="locked-when">불러오는 중…</p>
          : empty ? <p className="locked-when">이 기간에 상담 요청이 없어요</p>
          : <Funnel steps={steps} />}
        <p className="mini">
          {summary ? `${md(summary.period.from)}~${md(summary.period.to)} · ` : ''}
          오른쪽 %는 앞 단계 대비 · 병원 페이지 조회·시간 제안은 집계 전
        </p>
      </div>
    </section>
  );
}
