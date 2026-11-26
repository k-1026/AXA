import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import markup from './demo/markup.html?raw';
import { startDashboard } from './demo/legacy.js';
import './demo/demo.css';

// 옛 입점 병원 대시보드 (/dashboard/legacy, 보관용 — 기능을 새 /dashboard로 옮기면 삭제). 예전 dashboard/대시보드.html(포트 5175)을 그대로 옮겨 옴:
// 화면 틀은 demo/markup.html, 동작은 demo/legacy.js, 스타일은 demo/demo.css (.md-dashboard 아래로만)
export default function DashboardPage() {
  const host = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const el = host.current!;
    let stop: (() => void) | undefined;
    // 개발 모드 StrictMode가 바로 한 번 껐다 켜므로, 다음 틱에 시작해 스크립트가 두 번 돌지 않게
    const t = setTimeout(() => {
      el.innerHTML = markup;
      stop = startDashboard(el, { onLeave: () => navigate('/login', { replace: true, state: { who: 'staff' } }) });
    });
    return () => {
      clearTimeout(t);
      stop?.();
      el.innerHTML = '';
    };
  }, [navigate]);

  return <div ref={host} className="md-dashboard" />;
}
