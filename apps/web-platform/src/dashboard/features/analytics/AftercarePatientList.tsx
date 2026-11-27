// 사후관리 "처리 현황" 타일(신규 문의·미답변·처리 중·해결 완료)을 누르면 처리 현황과 반복 키워드 사이에 열리는 환자 목록
// 데이터는 처리 현황 타일이 불러온 GET /tenant/aftercare 그대로 (따로 부르지 않음). 환자를 누르면 그 사람의 사후관리 채팅을 엶
import { LANG, NAT, TRT, kday, md } from './bookingShared';
import { WaitBadge, clinicMinutes, useClinicClock } from './waitTime';
import { AC_FILTER, type AcFilter, type AcThread } from './AftercareStatusTiles';

const AC_ST = { new: '새 문의', in_progress: '처리 중', resolved: '해결됨' } as const;
const AC_CHIP = { new: 'st-pending', in_progress: 'st-proposed', resolved: 'st-visited' } as const;
export const acTid = (t: { id: string }) => `A-${t.id.slice(0, 4).toUpperCase()}`; // AftercareChat 목록과 같은 코드

export default function AftercarePatientList({ filter, list, sample, onClose, onOpen }: {
  filter: AcFilter; list: AcThread[] | null; sample: boolean; onClose: () => void; onOpen: (t: AcThread) => void;
}) {
  const { hours, now } = useClinicClock();
  const f = AC_FILTER[filter];
  // 기다린 시간이 긴 환자부터 (답할 게 없으면 최근 글 순)
  const rows = (list ?? []).filter(f.test).sort((a, b) =>
    (b.status !== 'resolved' && b.unanswered > 0 ? 1 : 0) - (a.status !== 'resolved' && a.unanswered > 0 ? 1 : 0)
    || (b.unanswered > 0 && a.unanswered > 0 ? a.last_message_at.localeCompare(b.last_message_at) : b.last_message_at.localeCompare(a.last_message_at)));
  const dPlus = (iso: string) => Math.max(0, Math.floor((now - new Date(iso).getTime()) / 864e5));

  return (
    <section className="card card-wide ac-plist" aria-label={`${f.label} 환자 목록`}>
      <header className="card-head">
        <span className={`badge ${sample ? 'badge-example' : 'badge-live'}`}>{sample ? '예시' : '실제'}</span>
        <h3>{f.label} 환자 {list ? `${rows.length}명` : ''}</h3>
        <button type="button" className="btn-ghost" onClick={onClose} aria-label="목록 닫기">닫기 ✕</button>
      </header>
      <div className="tbl-scroll">
        <table className="tbl req-tbl">
          <thead><tr><th>환자</th><th>국적·언어</th><th>진료 항목</th><th>방문</th><th>최근 메시지</th><th>기다린 시간</th><th>상태</th><th aria-label="채팅" /></tr></thead>
          <tbody>
            {rows.length ? rows.map((t) => {
              const waiting = t.status !== 'resolved' && t.unanswered > 0;
              return (
                <tr key={t.id} className="ac-prow" onClick={() => onOpen(t)}>
                  <td><b>{acTid(t)}</b></td>
                  <td>{NAT[t.nationality] || t.nationality} · {LANG[t.lang] || t.lang}</td>
                  <td>{t.tags[0] || TRT[t.treatment ?? ''] || t.treatment || '사후관리'}</td>
                  <td>{t.visited_slot ? <>{md(kday(t.visited_slot))} <small>D+{dPlus(t.visited_slot)}</small></> : '—'}</td>
                  <td className="ac-plast">{t.last_message ? t.last_message.slice(0, 36) : t.summary ?? '—'}{t.unanswered > 0 && <small> 답 안 한 글 {t.unanswered}개</small>}</td>
                  <td>{waiting ? <WaitBadge min={clinicMinutes(t.last_message_at, now, hours)} /> : <span className="mini">—</span>}</td>
                  <td><span className={`st-chip ${AC_CHIP[t.status]}`}>{AC_ST[t.status]}</span></td>
                  <td><button type="button" className={waiting ? 'btn' : 'btn-ghost'} onClick={(e) => { e.stopPropagation(); onOpen(t); }}>채팅 열기</button></td>
                </tr>
              );
            }) : (
              <tr><td colSpan={8} className="mini">{list ? `${f.label}에 해당하는 환자가 없어요` : '불러오는 중…'}</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="mini">환자를 누르면 아래 사후관리 채팅에서 그 사람의 대화가 열려요 (열람 기록이 남아요){sample && ' · 로그인 없는 미리보기라 예시 환자예요 — 채팅은 로그인해야 열려요'}</p>
    </section>
  );
}
