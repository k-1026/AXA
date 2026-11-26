// 홈 "오늘 할 일" 타일 4개 (옛 /dashboard/legacy 홈에서 가져옴, 화면은 새 디자인)
// 새 상담·오늘 방문: GET /tenant/analytics/summary 의 today · 미답변 사후관리: GET /tenant/aftercare (해결 안 된 대화의 unanswered)
// 결제 금액 입력은 백엔드 기능이 아직 없어 예시 숫자. 누르면 새 화면의 상담·예약 / 사후관리 / 진료·결제 확인 탭으로
import { useEffect, useState } from 'react';
import { API_BASE } from '../../../components/api';
import { readStaffToken } from '../../../features/staff/staffSession';
import { fmt } from './ui';

type Today = { newRequests: number; visitsToday: number; aftercareUnanswered: number };
type Thread = { status: string; unanswered: number };

async function get<T>(path: string, token: string): Promise<T> {
  const res = await fetch(API_BASE + path, { headers: { Authorization: 'Bearer ' + token } });
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

export default function TodayTiles({ onExpired }: { onExpired: () => void }) {
  const [today, setToday] = useState<Today | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const token = readStaffToken();
    if (!token) return;
    let alive = true;
    Promise.all([
      get<{ today: { newRequests: number; visitsToday: number } }>('/tenant/analytics/summary', token),
      get<Thread[]>('/tenant/aftercare', token),
    ])
      .then(([s, threads]) => {
        if (!alive) return;
        const open = threads.filter((t) => t.status !== 'resolved' && t.unanswered > 0).length;
        setToday({ newRequests: s.today.newRequests, visitsToday: s.today.visitsToday, aftercareUnanswered: open });
      })
      .catch((e: Error) => {
        if (!alive) return;
        if (e.message === '401') onExpired();
        else setError(true);
      });
    return () => { alive = false; };
  }, [onExpired]);

  const v = (n: number | undefined) => (today ? fmt(n ?? 0) : error ? '—' : '…');
  const ac = today?.aftercareUnanswered ?? 0;
  const tiles = [
    { label: '새 상담 요청', val: v(today?.newRequests), go: '답변하러 가기 →', href: '#booking', live: true },
    { label: '미답변 사후관리', val: v(today?.aftercareUnanswered), go: today ? (ac ? `답하지 않은 대화 ${ac}개 →` : '미답변 없음 →') : '불러오는 중…', href: '#aftercare', live: true, alert: ac > 0 },
    { label: '오늘 방문 예정', val: v(today?.visitsToday), go: '확정된 오늘 예약 →', href: '#booking', live: true },
    { label: '결제 금액 입력', val: '1', go: '방문 완료 R-1036 →', href: '#receipt', live: false },
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
