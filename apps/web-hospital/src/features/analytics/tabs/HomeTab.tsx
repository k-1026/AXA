import type { TabProps } from './props';
import { Card, Delta, Locked, LineChart, fmt } from '../ui';
import { KPI, TODAY } from '../sample';

export default function HomeTab({ data, mode, setup, toggleSetup }: TabProps) {
  const done = setup.filter((s) => s.done).length;
  const p = data.patients;
  const visitors = data.visitors.monthly.filter((m) => m.days >= 28);
  const operating = mode === 'operating';

  return (
    <div className="grid">
      {operating ? (
        <Card title="이번 달 성과 (지난달 대비)" kind="example" wide>
          <div className="kpis">
            {KPI.map((k) => (
              <div className="kpi" key={k.label}>
                <span className="kpi-label">{k.label}</span>
                <span className="kpi-val">{fmt(k.now)}<small>{k.unit}</small></span>
                <Delta now={k.now} prev={k.prev} unit={k.unit} lowerIsBetter={k.lowerIsBetter} />
              </div>
            ))}
          </div>
          <p className="note">예약 확정이 줄고 취소율이 올랐어요 → 상담·예약 탭에서 취소 사유를 확인해 보세요</p>
        </Card>
      ) : (
        <Locked
          title="이번 달 성과 (방문자·상담·예약·방문·취소율)"
          when="상세페이지 방문은 첫날부터, 상담·예약 지표는 첫 상담이 들어오면 채워져요"
          setup="아래 병원 정보 등록을 끝내면 환자 화면에 노출돼요"
        />
      )}

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

      {operating ? (
        <Card title="오늘 할 일" kind="example">
          <ul className="today">
            <li><b>{TODAY.newConsults}</b>새 상담</li>
            <li><b>{TODAY.bookingRequests}</b>예약 요청</li>
            <li><b>{TODAY.visitsToday}</b>오늘 방문 예정</li>
            <li className="is-alert"><b>{TODAY.unanswered}</b>미답변 문의</li>
          </ul>
        </Card>
      ) : (
        <Locked title="오늘 할 일 (새 상담·예약 요청·오늘 방문·미답변)" when="첫 상담이 들어오면 여기에 모여요" />
      )}

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
    </div>
  );
}
