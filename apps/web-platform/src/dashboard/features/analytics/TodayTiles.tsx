// 홈 "오늘 할 일" 타일 4개 (옛 /dashboard/legacy 홈에서 가져옴, 화면은 새 디자인)
// 새 상담·오늘 방문: GET /tenant/analytics/summary 의 today · 미답변 사후관리: GET /tenant/aftercare (해결 안 된 대화의 unanswered)
// 결제 금액 입력 = 방문 완료(visited)인데 결제 금액을 아직 안 넣은 예약 수 (11/27, GET /tenant/booking-requests?status=visited). 누르면 새 화면의 상담·예약 / 사후관리 / 진료·결제 확인 탭으로
import { useEffect, useState } from 'react';
import { readStaffToken } from '../../../features/staff/staffSession';
import { fmt } from './ui';
import { useAutoRefresh } from './autoRefresh';
import { monthSummaryPath } from './KpiTrends';
import { staffGet } from './staffGet';

type Today = { newRequests: number; visitsToday: number; aftercareUnanswered: number; toPay: number };
type Thread = { status: string; unanswered: number };

async function get<T>(path: string): Promise<T> {
  const res = await staffGet(path);
  if (!res.ok) throw new Error(String(res.status));
  return res.body as T;
}

export default function TodayTiles({ onExpired }: { onExpired: () => void }) {
  const [today, setToday] = useState<Today | null>(null);
  const [error, setError] = useState(false);
  const auto = useAutoRefresh(); // 새 요청 수가 바로 바뀌게 (30초마다·탭으로 돌아올 때)

  useEffect(() => {
    const token = readStaffToken();
    if (!token) return;
    let alive = true;
    Promise.all([
      // 홈 "기간 성과"(이번 달)와 같은 주소 → 서버에는 한 번만
      get<{ today: { newRequests: number; visitsToday: number } }>(monthSummaryPath()),
      get<Thread[]>('/tenant/aftercare'),
      get<unknown[]>('/tenant/booking-requests?status=visited'),
    ])
      .then(([s, threads, visited]) => {
        if (!alive) return;
        const open = threads.filter((t) => t.status !== 'resolved' && t.unanswered > 0).length;
        setToday({ newRequests: s.today.newRequests, visitsToday: s.today.visitsToday, aftercareUnanswered: open, toPay: visited.length });
      })
      .catch((e: Error) => {
        if (!alive) return;
        if (e.message === '401') onExpired();
        else setError(true);
      });
    return () => { alive = false; };
  }, [onExpired, auto]);

  const v = (n: number | undefined) => (today ? fmt(n ?? 0) : error ? '—' : '…');
  const ac = today?.aftercareUnanswered ?? 0;
  const tiles = [
    { label: '새 상담 요청', val: v(today?.newRequests), go: '답변하러 가기 →', href: '#booking', live: true },
    { label: '미답변 사후관리', val: v(today?.aftercareUnanswered), go: today ? (ac ? `답하지 않은 대화 ${ac}개 →` : '미답변 없음 →') : '불러오는 중…', href: '#aftercare', live: true, alert: ac > 0 },
    { label: '오늘 방문 예정', val: v(today?.visitsToday), go: '확정된 오늘 예약 →', href: '#booking', live: true },
    { label: '결제 금액 입력', val: v(today?.toPay), go: today ? (today.toPay ? '방문 완료 → 금액 입력 →' : '입력할 것 없음 →') : '불러오는 중…', href: '#receipt', live: true, alert: (today?.toPay ?? 0) > 0 },
  ];

  return (
    <section className="card card-wide">
      <header className="card-head">
        <span className="badge badge-live">실제</span>
        <h3>오늘 할 일</h3>
        {error && <span className="today-err">서버에서 불러오지 못했어요</span>}
      </header>
      <div className="today-tiles">
        {tiles.map((t) => (
          <a key={t.label} href={t.href} className={`today-tile${t.alert ? ' is-alert' : ''}`}>
            <span className="today-label">{t.label}{!t.live && <span className="badge badge-example">예시</span>}</span>
            <span className="today-val">{t.val}</span>
            <span className="today-go">{t.go}</span>
          </a>
        ))}
      </div>
    </section>
  );
}
