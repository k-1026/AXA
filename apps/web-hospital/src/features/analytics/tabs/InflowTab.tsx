import { useState } from 'react';
import type { TabProps } from './props';
import { BarList, Card, Locked, fmt, masked } from '../ui';
import { BUTTONS, CHANNELS, LANGUAGES, PRE_VISIT_QUESTIONS, SAMPLE_DISTRICT, TREATMENTS } from '../sample';
import { DEPT_LABEL } from '../types';

const CHANNEL_PRESETS = ['인스타그램', '블로그', '유치업체', '샤오홍슈', '카카오톡 채널'];

export default function InflowTab({ data, mode, dept }: TabProps) {
  const operating = mode === 'operating';
  const [links, setLinks] = useState<string[]>(['인스타그램']);
  const p = data.patients;
  const deptName = DEPT_LABEL[dept];
  const deptRow = dept === 'internal' ? '내과통합' : dept === 'dermatology' ? '피부과' : '안과';

  return (
    <div className="grid">
      <Card title="환자에게 보이는 우리 병원 페이지" kind="setup">
        <div className="preview">
          <div className="preview-photo">대표사진 없음</div>
          <div>
            <b>예시 {deptName}의원</b>
            <span className="mini">대구 {SAMPLE_DISTRICT} · {deptName}</span>
            <div className="preview-langs">
              {['한국어', 'English', '简体中文', '繁體中文', 'Tiếng Việt'].map((l) => <span key={l}>{l}</span>)}
            </div>
          </div>
        </div>
        <p className="note">5개 언어로 같은 형식이 보여요. 병원 소개·가격 안내를 채우면 여기에 반영돼요</p>
      </Card>

      <Card title="채널별 홍보 링크" kind="setup">
        <ul className="links">
          {links.map((l) => (
            <li key={l}><span>{l}</span><code>/hospitals/example?ch={encodeURIComponent(l)}</code></li>
          ))}
        </ul>
        <div className="chips">
          {CHANNEL_PRESETS.filter((c) => !links.includes(c)).map((c) => (
            <button type="button" key={c} className="chip-btn" onClick={() => setLinks([...links, c])}>+ {c}</button>
          ))}
        </div>
        <p className="note">링크마다 들어온 방문·상담·예약이 따로 집계돼요 (유입 경로)</p>
      </Card>

      {operating ? (
        <>
          <Card title="경로별 방문 → 상담 → 예약" kind="example" wide>
            <table className="tbl">
              <thead><tr><th>경로</th><th>방문</th><th>상담</th><th>예약</th><th>방문→예약</th></tr></thead>
              <tbody>
                {CHANNELS.map((c) => (
                  <tr key={c.name}>
                    <td>{c.name}</td><td>{fmt(c.visits)}</td><td>{c.consults}</td><td>{c.bookings}</td>
                    <td className={c.bookings / c.visits < 0.02 ? 'is-bad' : undefined}>{((c.bookings / c.visits) * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="note">인스타그램은 방문이 많은데 예약이 적어요 → 광고 내용과 병원 정보가 맞는지 확인</p>
          </Card>
          <Card title="언어별 상담·예약" kind="example">
            <table className="tbl">
              <thead><tr><th>언어</th><th>상담</th><th>예약</th></tr></thead>
              <tbody>
                {LANGUAGES.map((l) => <tr key={l.name}><td>{l.name}</td><td>{masked(l.consults)}</td><td>{masked(l.bookings)}</td></tr>)}
              </tbody>
            </table>
            <p className="note">베트남어 문의는 많은데 예약이 적어요 → 번역 안내·응대 가능 여부 점검. 5명 미만 칸은 숨김</p>
          </Card>
          <Card title="진료항목별 조회 → 상담" kind="example">
            <BarList items={TREATMENTS[dept].map((t) => ({ ...t, n: t.views }))} label={(t) => `조회 ${t.views} · 상담 ${t.consults}`} />
            <p className="note">조회는 많은데 상담이 적은 항목 → 비용·절차 설명 보강</p>
          </Card>
          <Card title="상세페이지에서 누른 버튼" kind="example">
            <BarList items={BUTTONS} />
          </Card>
          <Card title="자주 묻는 방문 전 질문" kind="example">
            <ul className="qs">
              {PRE_VISIT_QUESTIONS.map((q) => <li key={q.name}><b>{q.name}</b> <span>{q.n}건</span><em>→ {q.fix}</em></li>)}
            </ul>
          </Card>
        </>
      ) : (
        <>
          <Locked title="경로별 방문·상담·예약" when="홍보 링크로 첫 방문이 들어오면 채워져요" setup="위에서 홍보 링크 만들기" />
          <Locked title="언어·진료항목별 상담·예약, 누른 버튼, 방문 전 질문" when="방문·상담이 쌓이면 채워져요 (언어별 칸은 5명부터 공개)" />
        </>
      )}

      <Card title="대구에 오는 외국인환자 국적 (2025)" kind="public" source={p.source}>
        <BarList items={p.nationality2025.filter((n) => n.name !== '그 외 국가')} />
        <p className="mini">미국은 주한미군 등 거주자일 가능성 (팀 분석)</p>
      </Card>

      <Card title="대구 외국인환자 진료과 (2025)" kind="public" source={p.source}>
        <BarList items={p.departments2025.filter((d) => d.name !== '기타')} highlight={deptRow} />
      </Card>

      <Card title="성장 여지: 전국 증가율 vs 대구 점유율" kind="public" source={`${p.source} (팀 정리본)`}>
        <table className="tbl">
          <thead><tr><th>국적</th><th>전국 증가율 (24→25)</th><th>대구 점유율</th></tr></thead>
          <tbody>
            {[...p.growth].sort((a, b) => b.growth - a.growth).map((g) => (
              <tr key={g.name}><td>{g.name}</td><td>+{g.growth}%</td><td className={g.share < 1 ? 'is-bad' : undefined}>{g.share}%</td></tr>
            ))}
          </tbody>
        </table>
        <p className="note">전국에선 빠르게 느는데 대구 점유율이 1% 미만인 나라 → 그 언어 설명을 먼저 보강 (대구 전체 평균 1.0%)</p>
      </Card>

      <Card title={`대구 사는 외국인 ${fmt(data.residents.total)}명`} kind="public" source={data.residents.source}>
        <BarList items={data.residents.nationality.slice(0, 8)} />
      </Card>

      <Card title="외국인 방문자가 많은 구 (2025, 연인원)" kind="public" source={data.visitors.source}>
        <BarList items={data.visitors.byGu2025} highlight={SAMPLE_DISTRICT} label={(x) => `${Math.round(x.n / 10000)}만`} />
      </Card>

      <Card title="대구 '외국인 자주 찾는 병원'의 주요 시술" kind="public" source={data.favorite.source} wide>
        <ul className="fav">
          {data.favorite.hospitals.filter((h) => h.procedures.some(Boolean)).map((h) => (
            <li key={h.hospital}><b>{h.hospital}</b><span>{h.procedures.join(' · ')}</span></li>
          ))}
        </ul>
        <p className="note">메디컬코리아에서 외국인이 많이 본 대구 병원은 이 정도뿐이에요. 다국어 소개를 채우면 비교 우위가 돼요</p>
      </Card>
    </div>
  );
}
