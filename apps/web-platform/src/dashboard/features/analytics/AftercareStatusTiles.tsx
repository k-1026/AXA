// 사후관리 "처리 현황" 타일 6개 (운영 후 모드). 홈 "오늘 할 일"과 같은 모양
// 숫자는 실제 DB: GET /tenant/aftercare 의 대화(thread) 상태 new·in_progress·resolved 와 unanswered(답 안 한 환자 메시지 수)
// 누르면 답장 기능이 아직 있는 옛 화면(/dashboard/legacy#aftercare)으로
// 평균 첫 답변·만족도는 백엔드에 근거가 없어 예시 (sample.ts)
import { useEffect, useState } from 'react';
import { API_BASE } from '../../../components/api';
import { readStaffToken } from '../../../features/staff/staffSession';
import { fmt } from './ui';
import { AFTERCARE_FIRST_REPLY_MIN, SATISFACTION } from './sample';

type Thread = { status: 'new' | 'in_progress' | 'resolved'; unanswered: number };
type Counts = { fresh: number; unanswered: number; working: number; resolved: number };

export default function AftercareStatusTiles({ onExpired }: { onExpired: () => void }) {
  const [counts, setCounts] = useState<Counts | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const token = readStaffToken();
    if (!token) return;
    let alive = true;
    fetch(API_BASE + '/tenant/aftercare', { headers: { Authorization: 'Bearer ' + token } })
      .then(async (res) => {
        if (res.status === 401) throw new Error('401');
        if (!res.ok) throw new Error(String(res.status));
        return res.json() as Promise<Thread[]>;
      })
      .then((list) => {
        if (!alive) return;
        setCounts({
          fresh: list.filter((t) => t.status === 'new').length,
          unanswered: list.filter((t) => t.status !== 'resolved' && t.unanswered > 0).length,
          working: list.filter((t) => t.status === 'in_progress').length,
          resolved: list.filter((t) => t.status === 'resolved').length,
        });
      })
      .catch((e: Error) => {
        if (!alive) return;
        if (e.message === '401') onExpired();
        else setError(true);
      });
    return () => { alive = false; };
  }, [onExpired]);

  const v = (n: number | undefined) => (counts ? fmt(n ?? 0) : error ? '—' : '…');
  const href = '/dashboard/legacy#aftercare';
  const tiles = [
    { label: '신규 문의', val: v(counts?.fresh), go: '새 대화 확인하기 →' },
    { label: '미답변', val: v(counts?.unanswered), go: counts ? (counts.unanswered ? `답하지 않은 대화 ${counts.unanswered}개 →` : '미답변 없음 →') : '불러오는 중…', alert: (counts?.unanswered ?? 0) > 0 },
    { label: '처리 중', val: v(counts?.working), go: '진행 중인 대화 →' },
    { label: '해결 완료', val: v(counts?.resolved), go: '해결된 대화 보기 →' },
    { label: '평균 첫 답변', val: `${Math.floor(AFTERCARE_FIRST_REPLY_MIN / 60)}시간 ${AFTERCARE_FIRST_REPLY_MIN % 60}분`, go: '환자 문의 → 병원 첫 답장', example: true },
    { label: '만족도 (5점 만점)', val: `${SATISFACTION.score}`, go: `응답 ${SATISFACTION.responses}명 · 병원 내부용`, example: true, stars: SATISFACTION.score },
  ];

  return (
    <section className="card card-wide">
      <header className="card-head">
        <span className="badge badge-live">실제</span>
        <h3>처리 현황</h3>
        {error && <span className="today-err">서버에서 불러오지 못했어요</span>}
      </header>
      <div className="today-tiles">
        {tiles.map((t) => (
          <a key={t.label} href={href} className={`today-tile${t.alert ? ' is-alert' : ''}`}>
            <span className="today-label">{t.label}{t.example && <span className="badge badge-example">예시</span>}</span>
            <span className="today-val">{t.val}{t.stars != null && <small className="stars" aria-label={`5점 중 ${t.stars}점`}>{'★'.repeat(Math.round(t.stars))}{'☆'.repeat(5 - Math.round(t.stars))}</small>}</span>
            <span className="today-go">{t.go}</span>
          </a>
        ))}
      </div>
    </section>
  );
}
