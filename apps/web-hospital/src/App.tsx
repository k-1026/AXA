import { useEffect, useState } from 'react';
import type { DeptKey, Mode, PublicData } from './features/analytics/types';
import { DEPT_LABEL } from './features/analytics/types';
import { SAMPLE_DISTRICT, SETUP_ITEMS } from './features/analytics/sample';
import HomeTab from './features/analytics/tabs/HomeTab';
import InflowTab from './features/analytics/tabs/InflowTab';
import BookingTab from './features/analytics/tabs/BookingTab';
import AftercareTab from './features/analytics/tabs/AftercareTab';

const TABS = [
  { key: 'home', label: '홈', q: '이번 달 어떤 단계의 성과가 좋아지거나 떨어졌는가?', C: HomeTab },
  { key: 'inflow', label: '유입·관심', q: '어디에 홍보하고, 어떤 언어와 진료항목의 설명을 보강할까?', C: InflowTab },
  { key: 'booking', label: '상담·예약', q: '어느 단계에서 환자를 놓치나?', C: BookingTab },
  { key: 'aftercare', label: '사후관리', q: '어떤 안내를 미리 제공하고, 어떤 응대 과정을 개선할까?', C: AftercareTab },
] as const;

const tabFromHash = () => TABS.find((t) => `#${t.key}` === window.location.hash)?.key ?? 'home';

export default function App() {
  const [data, setData] = useState<PublicData | null>(null);
  const [error, setError] = useState(false);
  const [tab, setTab] = useState<string>(tabFromHash);
  const [mode, setMode] = useState<Mode>('initial');
  const [dept, setDept] = useState<DeptKey>('dermatology');
  const [setup, setSetup] = useState(SETUP_ITEMS);

  useEffect(() => {
    fetch('/data/dashboard-public.json').then((r) => r.json()).then(setData).catch(() => setError(true));
    const onHash = () => {
      setTab(tabFromHash());
      window.scrollTo(0, 0);
    };
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const current = TABS.find((t) => t.key === tab) ?? TABS[0];
  const toggleSetup = (key: string) => setSetup((s) => s.map((x) => (x.key === key ? { ...x, done: !x.done } : x)));

  return (
    <div className="app">
      <header className="top">
        <div className="brand">MediDaegu <span>병원</span></div>
        <div className="hospital">
          <b>예시 {DEPT_LABEL[dept]}의원</b>
          <span>대구 {SAMPLE_DISTRICT} · 가상 병원</span>
        </div>
        <label className="select">
          <span>진료과</span>
          <select value={dept} onChange={(e) => setDept(e.target.value as DeptKey)}>
            {Object.entries(DEPT_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <div className="mode" role="group" aria-label="데이터 상태">
          <button type="button" aria-pressed={mode === 'initial'} onClick={() => setMode('initial')}>초기 (데이터 없음)</button>
          <button type="button" aria-pressed={mode === 'operating'} onClick={() => setMode('operating')}>운영 후 (예시)</button>
        </div>
      </header>

      <nav className="tabs">
        {TABS.map((t) => (
          <a key={t.key} href={`#${t.key}`} className={t.key === current.key ? 'is-active' : undefined}>{t.label}</a>
        ))}
      </nav>

      <main className="main">
        <div className="tab-head">
          <h1>{current.label}</h1>
          <p>{current.q}</p>
          <p className="legend">
            <span className="badge badge-setup">설정</span> 병원이 채우는 것
            <span className="badge badge-public">공공</span> 대구 기준선 (실제 공공데이터)
            <span className="badge badge-example">예시</span> 가짜 운영 데이터
            <span className="badge badge-locked">집계 전</span> 데이터가 쌓이면 채워짐
          </p>
        </div>
        {error && <p className="note">공공데이터 파일을 불러오지 못했어요 (public/data/dashboard-public.json)</p>}
        {data && <current.C data={data} mode={mode} dept={dept} setup={setup} toggleSetup={toggleSetup} />}
      </main>

      <footer className="foot">프로토타입 · 병원 이름과 운영 숫자는 가상 · 공공 카드는 출처의 실제 값 · 통계는 구독 확장 플랜 기능</footer>
    </div>
  );
}
