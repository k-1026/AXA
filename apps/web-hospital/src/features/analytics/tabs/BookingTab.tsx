import { useState } from 'react';
import type { TabProps } from './props';
import { BarList, Card, Funnel, Locked, won } from '../ui';
import { CANCEL_REASONS, FIRST_REPLY, FUNNEL, PREFERRED_DAYS, REPEAT_CHANGES, SAMPLE_HOURS } from '../sample';
import { DEPT_LABEL } from '../types';

const DAYS = ['월', '화', '수', '목', '금', '토', '일'];
const FAQ_TEMPLATE = [
  { q: '통역이 되나요?', a: '응대 가능 언어와 통역 연결 방법을 적어 주세요' },
  { q: '어떻게 결제하나요?', a: '카드·현금·해외 결제 수단' },
  { q: '병원 위치·주차', a: '가까운 지하철역 출구, 주차 가능 여부' },
  { q: '예상 진료비를 미리 알 수 있나요?', a: '유치의료기관은 예상 진료비를 서면으로 안내해야 해요 (의료해외진출법 제8조)' },
];
const hm = (min: number) => `${Math.floor(min / 60)}시간 ${min % 60}분`;

export default function BookingTab({ data, mode, dept }: TabProps) {
  const operating = mode === 'operating';
  const [slots, setSlots] = useState<boolean[]>([true, true, true, true, true, true, false]);
  const h = data.hours.byDept[dept];
  const pct = (n: number) => Math.round((n / h.known) * 100);
  const prices = data.prices.byDept[dept] ?? [];
  const deptName = DEPT_LABEL[dept];

  return (
    <div className="grid">
      <Card title="예약 가능 요일" kind="setup">
        <div className="days">
          {DAYS.map((d, i) => (
            <button type="button" key={d} className={slots[i] ? 'day is-on' : 'day'} aria-pressed={slots[i]}
              onClick={() => setSlots(slots.map((v, j) => (j === i ? !v : v)))}>{d}</button>
          ))}
        </div>
        <p className="note">요일마다 받을 수 있는 시간대와 예약 수를 정하면 환자는 그 안에서만 신청해요</p>
      </Card>

      <Card title="자주 묻는 질문 기본 틀" kind="setup">
        <ul className="faq">
          {FAQ_TEMPLATE.map((f) => <li key={f.q}><b>{f.q}</b><span>{f.a}</span></li>)}
        </ul>
        <p className="note">KHIDI 다국어 서식집을 참고한 기본 질문. 답을 채우면 5개 언어로 보여요</p>
      </Card>

      {operating ? (
        <>
          <Card title="어느 단계에서 환자를 놓치나?" kind="example" wide>
            <Funnel steps={FUNNEL} />
            <p className="note">비율은 바로 앞 단계 대비. 상담을 시작하고도 예약 신청까지 가는 건 56% → 첫 답변 시간·비용 안내 확인. 신청 → 확정 65% → 희망 시간대와 확정 가능 시간 확인</p>
          </Card>
          <Card title="첫 답변 소요 시간" kind="example">
            <p className="big">{hm(FIRST_REPLY.medianMin)}<small> 중앙값</small></p>
            <p className="mini">지난달 {hm(FIRST_REPLY.prevMedianMin)} · 1시간 안에 답한 상담 {FIRST_REPLY.within1h}% · 상담 시간 밖 문의 {FIRST_REPLY.outsideHours}%</p>
            <p className="note">상담 가능 시간 기준으로 계산 (시간 밖 문의는 다음 상담 시작부터)</p>
          </Card>
          <Card title="예약 취소·변경 사유" kind="example">
            <BarList items={CANCEL_REASONS} />
            <p className="mini">변경을 2번 이상 요청한 예약 {REPEAT_CHANGES}건</p>
          </Card>
          <Card title="희망 요일과 확정률" kind="example">
            <BarList items={PREFERRED_DAYS.map((d) => ({ ...d, n: d.req }))} label={(d) => `${d.req}건 · 확정 ${Math.round((d.ok / d.req) * 100)}%`} />
            <p className="note">토요일에 신청이 몰리는데 확정률이 낮아요 → 토요일 예약 칸을 늘릴지 검토</p>
          </Card>
        </>
      ) : (
        <>
          <Locked title="단계별 전환 (조회 → 상담 → 신청 → 확정 → 방문)" when="첫 상담이 들어오면 채워져요" />
          <Locked title="첫 답변 시간, 취소·변경 사유, 희망 요일·시간대" when="상담·예약이 쌓이면 채워져요" setup="상담 가능 시간·예약 가능 요일 설정" />
        </>
      )}

      <Card title={`대구 ${deptName} 진료시간 (진료시간 신고 ${h.known}곳 기준)`} kind="public" source={data.hours.source}>
        <table className="tbl">
          <thead><tr><th></th><th>대구 {deptName}</th><th>우리 병원</th></tr></thead>
          <tbody>
            <tr><td>평일 저녁 7시 이후</td><td>{pct(h.night)}%</td><td>{SAMPLE_HOURS.night ? '진료' : '–'}</td></tr>
            <tr><td>토요일</td><td>{pct(h.saturday)}%</td><td>{SAMPLE_HOURS.saturday ? '진료' : '–'}</td></tr>
            <tr><td>일요일</td><td>{pct(h.sunday)}%</td><td>{SAMPLE_HOURS.sunday ? '진료' : '–'}</td></tr>
          </tbody>
        </table>
        <p className="mini">대구 {deptName} {h.total}곳 중 진료시간이 공개된 곳은 {h.known}곳 ({Math.round((h.known / h.total) * 100)}%) · 우리 병원 칸은 예시</p>
      </Card>

      <Card title={`대구 ${deptName} 비급여 가격 분포`} kind="public" source={prices.length ? data.prices.source : undefined}>
        {prices.length ? (
          <table className="tbl">
            <thead><tr><th>항목</th><th>기관</th><th>최소</th><th>중앙</th><th>최대</th></tr></thead>
            <tbody>
              {prices.slice(0, 5).map((p) => (
                <tr key={p.item}><td>{p.item}</td><td>{p.count}</td><td>{won(p.min)}</td><td><b>{won(p.median)}</b></td><td>{won(p.max)}</td></tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="note">대구 {deptName} 항목은 공공 비급여 가격이 없어요 (의원급은 공개 의무 없음). 가격 범위를 직접 등록하면 환자 화면에 &ldquo;병원 고지 가격&rdquo;으로 보여요</p>
        )}
        <p className="mini">다른 병원과 1:1 비교는 하지 않고 대구 전체 분포만 보여줘요</p>
      </Card>
    </div>
  );
}
