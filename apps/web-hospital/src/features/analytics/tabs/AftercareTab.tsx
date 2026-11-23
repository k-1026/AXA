import { useState } from 'react';
import type { TabProps } from './props';
import { Card, Locked } from '../ui';
import { AFTERCARE_CASE, AFTERCARE_KEYWORDS, AFTERCARE_STATUS, IMPROVEMENTS, SATISFACTION } from '../sample';

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

  return (
    <div className="grid">
      <Card title="방문 후 안내문·체크리스트" kind="setup" wide={!operating}>
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

      {operating ? (
        <>
          <Card title="처리 현황" kind="example">
            <ul className="today">
              {AFTERCARE_STATUS.map((s) => (
                <li key={s.name} className={s.name === '미답변' ? 'is-alert' : undefined}><b>{s.n}</b>{s.name}</li>
              ))}
            </ul>
          </Card>
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
          <Card title="대표 사례" kind="example">
            <p className="case-who">{AFTERCARE_CASE.who} · <span className="badge badge-locked">{AFTERCARE_CASE.keyword}</span></p>
            <p>{AFTERCARE_CASE.summary}</p>
            <p className="mini">이름·연락처·사진은 가림 · 원래 대화는 병원 직원만 열람</p>
          </Card>
          <Card title="개선 기록" kind="example">
            <table className="tbl">
              <thead><tr><th>날짜</th><th>바꾼 안내</th><th>관련 문의 (전→후)</th></tr></thead>
              <tbody>
                {IMPROVEMENTS.map((m) => <tr key={m.date}><td>{m.date}</td><td>{m.change}</td><td>{m.before} → {m.after}</td></tr>)}
              </tbody>
            </table>
          </Card>
          <Card title="만족도 (병원 내부용)" kind="example">
            <p className="big">{SATISFACTION.score}<small> / 5 · 응답 {SATISFACTION.responses}명</small></p>
            <p className="mini">환자 화면에 공개하지 않음 (치료경험담 광고 금지 유형)</p>
          </Card>
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
