import { useEffect, useState } from 'react';
import { Logo } from '../components/Logo';
import { Link, useNavigate } from 'react-router-dom';
import './analytics.css';
import { clearStaffToken, readStaffToken } from '../features/staff/staffSession';
import { loadHospitalProfile, type HospitalProfile } from './features/analytics/hospitalProfile';
import publicData from './data/dashboard-public.json';
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
  const data = publicData as PublicData;
  const navigate = useNavigate();
  const [tab, setTab] = useState<string>(tabFromHash);
  const [mode, setMode] = useState<Mode>('initial');
  const [dept, setDept] = useState<DeptKey>('dermatology');
  const [setup, setSetup] = useState(SETUP_ITEMS);
  // 헤더 병원 이름·구: 로그인한 계정의 병원 (/tenant/me + 병원 목록). 운영 후 모드에서만, 초기 모드는 예시 그대로
  const [profile, setProfile] = useState<HospitalProfile | null>(null);
  useEffect(() => {
    let alive = true;
    loadHospitalProfile(readStaffToken()).then((p) => { if (alive) setProfile(p); });
    return () => { alive = false; };
  }, []);
  const real = mode === 'operating' && profile;

  useEffect(() => {
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
    // 최상위 .hd 아래로만 이 화면 스타일이 적용됨 (analytics.css) — 환자 화면과 클래스 이름이 겹쳐도 섞이지 않게
    <div className="hd app">
      <header className="top">
        <Link to="/dashboard" className="brand" aria-label="MediDaegu 병원"><Logo /><span className="brand-tag">병원</span></Link>
        <div className="hospital">
          <b>{real ? profile.name : `예시 ${DEPT_LABEL[dept]}의원`}</b>
          <span>{real ? `대구${profile.district ? ` ${profile.district}` : ''}${profile.demo ? ' · 가상 병원' : ''}` : `대구 ${SAMPLE_DISTRICT} · 가상 병원`}</span>
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
        <button type="button" className="btn-ghost" onClick={() => { clearStaffToken(); navigate('/login', { replace: true, state: { who: 'staff' } }); }}>로그아웃</button>
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
            <span className="badge badge-live">실제</span> 우리 병원 DB 데이터
            <span className="badge badge-setup">설정</span> 병원이 채우는 것
            <span className="badge badge-public">공공</span> 대구 기준선 (실제 공공데이터)
            <span className="badge badge-example">예시</span> 가짜 운영 데이터
            <span className="badge badge-locked">집계 전</span> 데이터가 쌓이면 채워짐
          </p>
        </div>
        <current.C data={data} mode={mode} dept={dept} setup={setup} toggleSetup={toggleSetup} />
      </main>

      <footer className="foot">프로토타입 · 병원 이름과 운영 숫자는 가상 · 공공 카드는 출처의 실제 값 · 통계(분석 탭)는 기본·프리미엄 모두 사용</footer>
    </div>
  );
}
