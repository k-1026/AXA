// 상담·예약 "예약 현황" 타일 4개 (운영 후 모드). 옛 /dashboard/legacy 상담·예약 탭 위 숫자를 홈 "오늘 할 일" 모양으로
// 숫자는 실제 DB: GET /tenant/booking-requests?status=… (pending·proposed·confirmed·visited·no_show)
// 이번 주 확정 = 확정된 진료일(confirmed_slot)이 이번 주(월~일, 한국 날짜)인 확정·방문·미방문 예약
// 반복 변경(2회 이상)은 근거 데이터가 백엔드에 없어 예시. 누르면 확정·답장 기능이 있는 옛 화면으로
import { useEffect, useState } from 'react';
import { readStaffToken } from '../../../features/staff/staffSession';
import { REPEAT_CHANGES } from './sample';
import { fmt, goToCard } from './ui';
import { staffGet } from './staffGet';

type Req = { status: string; confirmed_slot: string | null };
type Counts = { pending: number; proposed: number; thisWeek: number };
const STATUSES = ['pending', 'proposed', 'confirmed', 'visited', 'no_show'] as const;

// 한국 날짜 (YYYY-MM-DD)
const kday = (d: Date) => new Date(d.getTime() + 9 * 3600e3).toISOString().slice(0, 10);
function thisWeekKst(): [string, string] {
  const today = new Date(kday(new Date()) + 'T00:00:00Z');
  const mon = new Date(today.getTime() - ((today.getUTCDay() + 6) % 7) * 864e5);
  return [mon.toISOString().slice(0, 10), new Date(mon.getTime() + 6 * 864e5).toISOString().slice(0, 10)];
}

// rev가 바뀌면 다시 불러옴 (처리·자동 새로고침). 불러오는 동안 이전 숫자는 그대로 둠
export default function BookingStatusTiles({ rev = 0, onExpired }: { rev?: number; onExpired: () => void }) {
  const [counts, setCounts] = useState<Counts | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const token = readStaffToken();
    if (!token) return;
    let alive = true;
    Promise.all(STATUSES.map(async (s) => {
      const res = await staffGet(`/tenant/booking-requests?status=${s}`);
      if (res.status === 401) throw new Error('401');
      if (!res.ok) throw new Error(String(res.status));
      return res.body as Req[];
    }))
      .then(([pending, proposed, ...done]) => {
        if (!alive) return;
        const [mon, sun] = thisWeekKst();
        const inWeek = (r: Req) => { if (!r.confirmed_slot) return false; const d = kday(new Date(r.confirmed_slot)); return d >= mon && d <= sun; };
        setCounts({ pending: pending.length, proposed: proposed.length, thisWeek: done.flat().filter(inWeek).length });
      })
      .catch((e: Error) => {
        if (!alive) return;
        if (e.message === '401') onExpired();
        else setError(true);
      });
    return () => { alive = false; };
  }, [onExpired, rev]);

  const v = (n: number | undefined) => (counts ? fmt(n ?? 0) : error ? '—' : '…');
  // 누르면 같은 탭 안의 카드로 이동 (예전에는 옛 대시보드 /dashboard/legacy 로 갔음)
  const tiles = [
    { label: '대기', val: v(counts?.pending), go: counts?.pending ? '확정·시간 제안하러 가기 →' : '대기 중인 요청 없음 →', alert: (counts?.pending ?? 0) > 0, live: true, to: '요청 목록' },
    { label: '시간 제안함', val: v(counts?.proposed), go: '환자 답을 기다리는 중 →', live: true, to: '요청 목록' },
    { label: '이번 주 확정', val: v(counts?.thisWeek), go: `${thisWeekKst().map((d) => `${+d.slice(5, 7)}/${+d.slice(8)}`).join('~')} 진료 예약 →`, live: true, to: '예약 캘린더' },
    { label: '반복 변경 (2회 이상)', val: fmt(REPEAT_CHANGES), go: '취소·변경 사유 보기 →', live: false, to: '예약 취소·변경 사유' },
  ];

  return (
    <section className="card card-wide">
      <header className="card-head">
        <span className="badge badge-live">실제</span>
        <h3>예약 현황</h3>
        {error && <span className="today-err">서버에서 불러오지 못했어요</span>}
      </header>
      <div className="today-tiles">
        {tiles.map((t) => (
          <a key={t.label} href="#booking" onClick={(e) => { e.preventDefault(); goToCard(t.to); }} className={`today-tile${t.alert ? ' is-alert' : ''}`}>
            <span className="today-label">{t.label}{!t.live && <span className="badge badge-example">예시</span>}</span>
            <span className="today-val">{t.val}</span>
            <span className="today-go">{t.go}</span>
          </a>
        ))}
      </div>
    </section>
  );
}
