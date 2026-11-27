// 사후관리 "처리 현황" 타일 6개 (운영 후 모드). 홈 "오늘 할 일"과 같은 모양
// 숫자는 실제 DB: GET /tenant/aftercare 의 대화(thread) 상태 new·in_progress·resolved 와 unanswered(답 안 한 환자 메시지 수)
// 신규 문의·미답변·처리 중·해결 완료를 누르면 아래에 해당 환자 목록(AftercarePatientList)이 열림 (한 번 더 누르면 닫힘)
// 로그인 없는 미리보기(?preview=1)에서는 예시 대화로 셈
// 평균 첫 답변·만족도는 백엔드에 근거가 없어 예시 (sample.ts)
import { useEffect, useState } from 'react';
import { API_BASE } from '../../../components/api';
import { isStaffPreview, readStaffToken } from '../../../features/staff/staffSession';
import { fmt, goToCard } from './ui';
import { AFTERCARE_FIRST_REPLY_MIN, SAMPLE_AFTERCARE_THREADS, SATISFACTION } from './sample';

// GET /tenant/aftercare 한 줄 (환자 목록에서 쓰는 것까지)
export type AcThread = {
  id: string; request_id: string; status: 'new' | 'in_progress' | 'resolved'; unanswered: number; tags: string[]; summary: string | null;
  lang: string; nationality: string; treatment: string | null; visited_slot: string | null; last_message_at: string; last_message: string | null;
};
export type AcFilter = 'fresh' | 'unanswered' | 'working' | 'resolved';
export const AC_FILTER: Record<AcFilter, { label: string; test: (t: AcThread) => boolean }> = {
  fresh: { label: '신규 문의', test: (t) => t.status === 'new' },
  unanswered: { label: '미답변', test: (t) => t.status !== 'resolved' && t.unanswered > 0 },
  working: { label: '처리 중', test: (t) => t.status === 'in_progress' },
  resolved: { label: '해결 완료', test: (t) => t.status === 'resolved' },
};
type Counts = Record<AcFilter, number>;

export default function AftercareStatusTiles({ onExpired, filter, onFilter, onList }: {
  onExpired: () => void; filter?: AcFilter | null; onFilter?: (f: AcFilter | null) => void; onList?: (list: AcThread[] | null, sample: boolean) => void;
}) {
  const [counts, setCounts] = useState<Counts | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const token = readStaffToken();
    const count = (list: AcThread[]) => Object.fromEntries((Object.keys(AC_FILTER) as AcFilter[]).map((k) => [k, list.filter(AC_FILTER[k].test).length])) as Counts;
    if (!token) {
      if (isStaffPreview()) { const list = SAMPLE_AFTERCARE_THREADS(); setCounts(count(list)); onList?.(list, true); }
      return;
    }
    let alive = true;
    fetch(API_BASE + '/tenant/aftercare', { headers: { Authorization: 'Bearer ' + token } })
      .then(async (res) => {
        if (res.status === 401) throw new Error('401');
        if (!res.ok) throw new Error(String(res.status));
        return res.json() as Promise<AcThread[]>;
      })
      .then((list) => {
        if (!alive) return;
        setCounts(count(list));
        onList?.(list, false);
      })
      .catch((e: Error) => {
        if (!alive) return;
        if (e.message === '401') onExpired();
        else { setError(true); onList?.(null, false); }
      });
    return () => { alive = false; };
  }, [onExpired, onList]);

  const v = (n: number | undefined) => (counts ? fmt(n ?? 0) : error ? '—' : '…');
  const tiles: { label: string; val: string; go: string; key?: AcFilter; alert?: boolean; example?: boolean; stars?: number }[] = [
    { key: 'fresh', label: '신규 문의', val: v(counts?.fresh), go: '새 대화 환자 보기 →' },
    { key: 'unanswered', label: '미답변', val: v(counts?.unanswered), go: counts ? (counts.unanswered ? `답하지 않은 환자 ${counts.unanswered}명 →` : '미답변 없음 →') : '불러오는 중…', alert: (counts?.unanswered ?? 0) > 0 },
    { key: 'working', label: '처리 중', val: v(counts?.working), go: '진행 중인 환자 보기 →' },
    { key: 'resolved', label: '해결 완료', val: v(counts?.resolved), go: '해결된 환자 보기 →' },
    { label: '평균 첫 답변', val: `${Math.floor(AFTERCARE_FIRST_REPLY_MIN / 60)}시간 ${AFTERCARE_FIRST_REPLY_MIN % 60}분`, go: '사후관리 채팅으로 →', example: true },
    { label: '만족도 (5점 만점)', val: `${SATISFACTION.score}`, go: `응답 ${SATISFACTION.responses}명 · 병원 내부용`, example: true, stars: SATISFACTION.score },
  ];

  return (
    <section className="card card-wide">
      <header className="card-head">
        <span className={`badge ${!readStaffToken() && counts ? 'badge-example' : 'badge-live'}`}>{!readStaffToken() && counts ? '예시' : '실제'}</span>
        <h3>처리 현황</h3>
        {error && <span className="today-err">서버에서 불러오지 못했어요</span>}
      </header>
      <div className="today-tiles has-sep">
        {tiles.map((t, i) => [
          // 해결 완료(실제)와 평균 첫 답변(예시) 사이 얇은 구분선
          i === 4 && <span key="sep" className="today-sep" aria-hidden />,
          t.key && onFilter ? (
            <button key={t.label} type="button" aria-pressed={filter === t.key} onClick={() => onFilter(filter === t.key ? null : t.key!)}
              className={`today-tile${t.alert ? ' is-alert' : ''}${filter === t.key ? ' is-picked' : ''}`}>
              <span className="today-label">{t.label}</span>
              <span className="today-val">{t.val}</span>
              <span className="today-go">{filter === t.key ? '목록 닫기 ↑' : t.go}</span>
            </button>
          ) : (
          // 평균 첫 답변 → 아래 사후관리 채팅으로 이동, 만족도 → 아직 볼 화면이 없어 누르지 않는 칸 (예전에는 둘 다 옛 대시보드로 갔음)
          <a key={t.label} href="#aftercare" onClick={(e) => { e.preventDefault(); if (!t.stars) goToCard('사후관리 채팅'); }}
            className={`today-tile${t.alert ? ' is-alert' : ''}${t.stars != null ? ' is-static' : ''}`} {...(t.stars != null ? { 'aria-disabled': true, tabIndex: -1 } : {})}>
            <span className="today-label">{t.label}{t.example && <span className="badge badge-example">예시</span>}</span>
            <span className="today-val">{t.val}{t.stars != null && <small className="stars" aria-label={`5점 중 ${t.stars}점`}>{'★'.repeat(Math.round(t.stars))}{'☆'.repeat(5 - Math.round(t.stars))}</small>}</span>
            <span className="today-go">{t.go}</span>
          </a>
          ),
        ])}
      </div>
    </section>
  );
}
