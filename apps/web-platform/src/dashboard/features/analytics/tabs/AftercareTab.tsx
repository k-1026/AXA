import { useCallback, useRef, useState } from 'react';
import type { TabProps } from './props';
import { Card, Locked } from '../ui';
import { AFTERCARE_KEYWORDS } from '../sample';
import AftercareStatusTiles, { type AcFilter, type AcThread } from '../AftercareStatusTiles';
import AftercarePatientList, { acTid } from '../AftercarePatientList';
import AftercareChat from '../AftercareChat';
import { useStaffExpired } from '../useStaffExpired';

const GUIDE_TEMPLATE = [
  '귀국 후 주의사항 (병원이 작성)',
  '이상이 있을 때 연락할 곳·연락 가능 시간',
  '재방문·경과 확인 일정',
  '진료비 영수증·진료기록 사본 받는 방법',
  '분쟁·불만 상담: 메디컬코리아 외국인환자 지원',
];

export default function AftercareTab({ mode }: TabProps) {
  const operating = mode === 'operating';
  const [checked, setChecked] = useState<boolean[]>(GUIDE_TEMPLATE.map((_, i) => i > 2));
  const onExpired = useStaffExpired();
  const [rev, setRev] = useState(0); // 채팅에서 답장·상태를 바꾸면 처리 현황도 다시 불러옴
  // 처리 현황 타일을 누르면 열리는 환자 목록 (처리 현황과 반복 키워드 사이)
  const [filter, setFilter] = useState<AcFilter | null>(null);
  const [threads, setThreads] = useState<{ list: AcThread[] | null; sample: boolean }>({ list: null, sample: false });
  const onList = useCallback((list: AcThread[] | null, sample: boolean) => setThreads({ list, sample }), []);
  const [openMsg, setOpenMsg] = useState('');
  const root = useRef<HTMLDivElement>(null);
  // 환자를 누르면 아래 사후관리 채팅 목록에서 같은 대화(A-코드)를 눌러 엶 — 채팅 컴포넌트는 그대로 둠
  const openChat = (t: AcThread) => {
    const btn = [...(root.current?.querySelectorAll<HTMLButtonElement>('.chat-list .chat-item') ?? [])]
      .find((b) => b.querySelector('b')?.textContent?.startsWith(acTid(t) + ' '));
    if (!btn) { setOpenMsg(`${acTid(t)} 대화를 사후관리 채팅에서 찾지 못했어요${threads.sample ? ' (예시 환자는 로그인해야 열 수 있어요)' : ''}`); return; }
    setOpenMsg('');
    btn.click();
    btn.closest('.card')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="grid" ref={root}>
      {/* 방문 후 안내문·체크리스트: 초기 모드에서만 (운영 후 모드에서는 뺌) */}
      {!operating && (
      <Card title="방문 후 안내문·체크리스트" kind="setup" wide>
        <ul className="checklist">
          {GUIDE_TEMPLATE.map((g, i) => (
            <li key={g}>
              <label>
                <input type="checkbox" checked={checked[i]} onChange={() => setChecked(checked.map((v, j) => (j === i ? !v : v)))} />
                {g}
              </label>
            </li>
          ))}
        </ul>
        <p className="note">KHIDI 다국어 서식집을 참고한 기본 항목. 방문 완료 환자에게 언어별로 자동 전달돼요. 사후 진료 판단은 의료진이 상담 화면에서 직접 해요</p>
      </Card>
      )}

      {operating ? (
        <>
          <AftercareStatusTiles key={rev} onExpired={onExpired} filter={filter} onFilter={(f) => { setFilter(f); setOpenMsg(''); }} onList={onList} />
          {filter && (
            <AftercarePatientList filter={filter} list={threads.list} sample={threads.sample} onClose={() => setFilter(null)} onOpen={openChat} />
          )}
          {openMsg && <p className="dlg-err card-wide" role="status">{openMsg}</p>}
          {/* 반복 키워드(1) | 사후관리 채팅(2) 한 줄 */}
          <div className="row-1-2">
          <Card title="반복 키워드 (지난달 대비)" kind="example">
            <table className="tbl">
              <thead><tr><th>키워드</th><th>이번 달</th><th>지난달</th></tr></thead>
              <tbody>
                {AFTERCARE_KEYWORDS.map((k) => (
                  <tr key={k.name}><td>{k.name}</td><td className={k.now > k.prev ? 'is-bad' : undefined}>{k.now}</td><td>{k.prev}</td></tr>
                ))}
              </tbody>
            </table>
            <p className="note">&lsquo;안내 부족&rsquo;과 &lsquo;비용 설명&rsquo;이 늘었어요 → 안내문에 미리 넣을 내용 확인</p>
          </Card>
          <AftercareChat rev={rev} onExpired={onExpired} onChanged={() => setRev((n) => n + 1)} />
          </div>
        </>
      ) : (
        <>
          <Locked title="처리 현황 (신규·미답변·처리 중·해결)" when="방문 완료 환자가 첫 문의를 남기면 채워져요" />
          <Locked title="반복 키워드·주제별 추이·대표 사례·개선 기록" when="문의가 쌓이면 채워져요" setup="방문 후 안내문 작성" />
        </>
      )}
      <p className="tab-foot">사후관리 통계로 쓸 공공데이터는 거의 없어서, 초기 화면은 안내문 설정 중심이에요</p>
    </div>
  );
}
