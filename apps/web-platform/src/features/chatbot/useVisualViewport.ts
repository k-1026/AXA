import { useEffect } from 'react';

// 모바일 키보드가 열리면 보이는 영역(visualViewport) 높이로 화면을 줄여 입력창이 가려지지 않게 한다
// iOS Safari는 키보드가 열려도 레이아웃 높이가 그대로라 직접 맞춰야 함
export function useVisualViewport() {
  useEffect(() => {
    const vv = window.visualViewport;
    const root = document.documentElement;
    const apply = () => {
      root.style.setProperty('--chat-vh', `${vv ? vv.height : window.innerHeight}px`);
      // 키보드가 열릴 때 브라우저가 페이지를 위로 밀어 올린 만큼 되돌린다
      if (vv && vv.offsetTop > 0) window.scrollTo(0, 0);
    };
    apply();
    vv?.addEventListener('resize', apply);
    vv?.addEventListener('scroll', apply);
    window.addEventListener('resize', apply);
    document.body.classList.add('chat-open'); // 뒤 페이지 스크롤 막기
    return () => {
      vv?.removeEventListener('resize', apply);
      vv?.removeEventListener('scroll', apply);
      window.removeEventListener('resize', apply);
      root.style.removeProperty('--chat-vh');
      document.body.classList.remove('chat-open');
    };
  }, []);
}
