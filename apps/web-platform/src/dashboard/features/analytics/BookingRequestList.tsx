// 상담·예약 "요청 목록" (운영 후 모드). 옛 /dashboard/legacy 상담·예약 탭의 표를 새 디자인으로
// 대기·시간 제안함·확정 요청 (GET /tenant/booking-requests), 줄마다 처리 버튼 → 작은 창에서 확정·시간 제안·거절·방문 처리
import { useCallback, useEffect, useState } from 'react';
import { readStaffToken } from '../../../features/staff/staffSession';
import {
  ACTIONS, ActionDialog, Expired, ST, loadOpenRequests, reqId, reqTitle, reqWho, slotLabel, type ActionMode, type DbReq,
} from './bookingShared';

export default function BookingRequestList({ rev, onExpired, onChanged }: { rev: number; onExpired: () => void; onChanged: () => void }) {
  const [rows, setRows] = useState<DbReq[] | null>(null);
  const [error, setError] = useState(false);
  const [open, setOpen] = useState<{ req: DbReq; mode: ActionMode } | null>(null);
  const [toast, setToast] = useState('');

  const load = useCallback(async () => {
    try { setRows(await loadOpenRequests()); setError(false); }
    catch (e) { if (e instanceof Expired) onExpired(); else setError(true); }
  }, [onExpired]);
  useEffect(() => { if (readStaffToken()) load(); }, [load, rev]);

  const count = (s: string) => rows?.filter((r) => r.status === s).length ?? 0;

  return (
    <section className="card card-wide">
      <header className="card-head">
        <span className="badge badge-live">실제</span>
        <h3>요청 목록</h3>
        <span className="mini">{rows ? `대기 ${count('pending')} · 제안 ${count('proposed')} · 확정 ${count('confirmed')}` : error ? '서버에서 불러오지 못했어요' : '불러오는 중…'}</span>
      </header>
      {toast && <p className="dlg-toast" role="status">{toast}</p>}
      <div className="tbl-scroll">
        <table className="tbl req-tbl">
          <thead><tr><th>요청</th><th>국적·언어</th><th>진료 항목</th><th>희망·확정 시간</th><th>비자</th><th>상태</th><th aria-label="처리" /></tr></thead>
          <tbody>
            {rows?.length ? rows.map((r) => (
              <tr key={r.id}>
                <td><b>{reqId(r)}</b></td>
                <td>{reqWho(r)}</td>
                <td>{reqTitle(r)}</td>
                <td>
                  {r.status !== 'pending' && r.confirmed_slot ? slotLabel(r.confirmed_slot) : r.preferred_slots[0] ? slotLabel(r.preferred_slots[0]) : '—'}
                  {r.status === 'pending' && r.preferred_slots.length > 1 && <small> 외 {r.preferred_slots.length - 1}개</small>}
                </td>
                <td>{r.visa_needed ? <span className="st-chip st-proposed">예약확인서 필요</span> : <span className="mini">불필요</span>}</td>
                <td><span className={`st-chip st-${r.status}`}>{ST[r.status]}</span></td>
                <td className="req-acts">
                  {(ACTIONS[r.status] ?? []).map((a) => (
                    <button key={a.mode} type="button" className={a.mode === 'reject' || a.mode === 'no_show' ? 'btn-ghost is-danger' : a.mode === 'confirm' || a.mode === 'visited' ? 'btn' : 'btn-ghost'}
                      onClick={() => { setToast(''); setOpen({ req: r, mode: a.mode }); }}>{a.label}</button>
                  ))}
                </td>
              </tr>
            )) : (
              <tr><td colSpan={7} className="mini">{rows ? '처리할 요청이 없어요' : error ? '—' : '불러오는 중…'}</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="mini">국내 거주 외국인(외국인등록·국내거소)은 가입 때 구분되어 상담 요청 버튼이 보이지 않아요. 병원 정보·진료시간·전화번호만 볼 수 있어요</p>

      {open && (
        <ActionDialog req={open.req} mode={open.mode} onExpired={onExpired} onClose={() => { setOpen(null); load(); }}
          onDone={(msg) => { setOpen(null); if (msg) setToast(msg); onChanged(); }} />
      )}
    </section>
  );
}
