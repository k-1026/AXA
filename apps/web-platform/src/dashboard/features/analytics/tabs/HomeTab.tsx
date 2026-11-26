import { useState } from 'react';
import type { TabProps } from './props';
import { Card, Locked, LineChart, fmt } from '../ui';
import TodayTiles from '../TodayTiles';
import KpiTrends, { type Summary } from '../KpiTrends';
import FunnelCard from '../FunnelCard';
import { useStaffExpired } from '../useStaffExpired';

export default function HomeTab({ data, mode, setup, toggleSetup }: TabProps) {
  const done = setup.filter((s) => s.done).length;
  const p = data.patients;
  const visitors = data.visitors.monthly.filter((m) => m.days >= 28);
  const operating = mode === 'operating';
  const [summary, setSummary] = useState<Summary | null>(null); // 기간 성과에서 고른 기간 합계 → 요청·체결·방문 카드
  const onExpired = useStaffExpired(); // 로그인 만료(401) → 로그인 화면으로

  // 공공 카드 3개: 항상 홈 맨 아래
  const publicCards = (
    <>
      <Card title="대구 등록 유치의료기관" kind="public" source={data.registered.source}>
        <p className="big">{fmt(data.registered.total)}<small>곳</small></p>
        <p className="note">등록번호를 확인하면 환자 화면에 &ldquo;등록 유치의료기관&rdquo;이 표시돼요. 등록 전이라면 메디컬코리아에서 신청할 수 있어요</p>
        <p className="mini">{data.registered.byType.map((t) => `${t.name} ${t.n}`).join(' · ')}</p>
      </Card>

      <Card title="대구 외국인환자 (실환자)" kind="public" source={p.source}>
        <p className="big">{fmt(p.summary2025.real)}<small>명 · 2025</small></p>
        <LineChart points={p.byYear.map((y) => ({ x: String(y.year).slice(2), y: y.n }))} yLabel={(n) => `${Math.round(n / 1000)}천`} />
        <p className="mini">여성 {p.summary2025.female}% · 남성 {p.summary2025.male}%</p>
      </Card>

      <Card title="대구 외국인 방문자 (월별 연인원)" kind="public" source={data.visitors.source}>
        <LineChart points={visitors.map((m) => ({ x: m.month.slice(2).replace('-', '.'), y: m.n }))} yLabel={(n) => `${Math.round(n / 10000)}만`} />
        <p className="mini">같은 사람이 여러 날 있으면 여러 번 셈 · 의료 목적 여부는 알 수 없음 · 마지막 달은 다 찬 달까지만</p>
      </Card>
    </>
  );

  if (operating) {
    // 운영 후: 오늘 할 일 → 기간 성과 → 요청·체결·방문(첫 칸) → 공공 카드 3개 (한 줄, 윗선 맞춤)
    return (
      <div className="grid">
        <TodayTiles onExpired={onExpired} />
        <KpiTrends onExpired={onExpired} onSummary={setSummary} />
        <div className="row3">
          <FunnelCard summary={summary} />
        </div>
        <div className="row3">{publicCards}</div>
      </div>
    );
  }

  return (
    <div className="grid">
      <Locked
        title="이번 달 성과 (방문자·상담·예약·방문·취소율)"
        when="상세페이지 방문은 첫날부터, 상담·예약 지표는 첫 상담이 들어오면 채워져요"
        setup="아래 병원 정보 등록을 끝내면 환자 화면에 노출돼요"
      />

      <Card
        title={`병원 정보 등록 ${done}/${setup.length}`}
        kind="setup"
        action={<span className="progress"><span style={{ width: `${(done / setup.length) * 100}%` }} /></span>}
      >
        <ul className="setup">
          {setup.map((s) => (
            <li key={s.key} className={s.done ? 'is-done' : undefined}>
              <span className="setup-mark" aria-hidden>{s.done ? '✓' : ''}</span>
              <span className="setup-text">
                <b>{s.label}</b>{s.from && <em> · {s.from}에서 불러옴</em>}
                <span>{s.hint}</span>
              </span>
              <button type="button" className={s.done ? 'btn-ghost' : 'btn'} onClick={() => toggleSetup(s.key)}>
                {s.done ? '수정' : '입력하기'}
              </button>
            </li>
          ))}
        </ul>
      </Card>

      <Locked title="오늘 할 일 (새 상담·예약 요청·오늘 방문·미답변)" when="첫 상담이 들어오면 여기에 모여요" />

      {publicCards}
    </div>
  );
}
