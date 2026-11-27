import { useEffect, useState } from 'react';

// 대시보드 자동 새로고침 (11/26): 환자가 다른 화면에서 보낸 새 요청이 열려 있는 대시보드에 안 나타나던 것.
// 화면이 보일 때 30초마다, 그리고 다른 탭·창에서 돌아올 때 숫자를 하나 올린다 → 이 숫자를 useEffect 의존값에 넣으면 다시 불러옴.
// 탭이 숨겨져 있을 때는 부르지 않는다 (서버 부담·Vercel 함수 호출 줄이기)
export const AUTO_REFRESH_MS = 30_000;

export function useAutoRefresh(ms = AUTO_REFRESH_MS): number {
  const [n, setN] = useState(0);
  useEffect(() => {
    const bump = () => { if (document.visibilityState === 'visible') setN((x) => x + 1); };
    const timer = window.setInterval(bump, ms);
    document.addEventListener('visibilitychange', bump);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', bump);
    };
  }, [ms]);
  return n;
}
