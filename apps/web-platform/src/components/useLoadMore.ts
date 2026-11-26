import { useCallback, useEffect, useState } from 'react';

// 목록 "더 보기": 처음엔 버튼, 한 번 누르면 그다음부터는 끝까지 스크롤하면 자동으로 더 불러옴 (무한 스크롤)
// resetKey(필터 등)가 바뀌면 처음 개수로 돌아가지만, 자동 불러오기는 켜 둔 채로 둔다
// autoFromStart: 버튼 없이 처음부터 무한 스크롤 (가격 가이드, 2026-11-26)
export function useLoadMore(total: number, pageSize: number, resetKey: string, autoFromStart = false) {
  const [shown, setShown] = useState(pageSize);
  const [auto, setAuto] = useState(autoFromStart);
  const [sentinel, setSentinel] = useState<HTMLElement | null>(null);
  const [prevKey, setPrevKey] = useState(resetKey);

  // 필터가 바뀐 렌더에서 바로 처음 개수로 (이전 개수로 한 번 그려지지 않게, React 문서의 "이전 값 저장" 방식)
  if (prevKey !== resetKey) {
    setPrevKey(resetKey);
    setShown(pageSize);
  }

  const hasMore = shown < total;

  const more = useCallback(() => {
    setAuto(true);
    setShown((s) => s + pageSize);
  }, [pageSize]);

  useEffect(() => {
    if (!auto || !hasMore || !sentinel) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) setShown((s) => s + pageSize);
      },
      { rootMargin: '400px 0px' },
    );
    io.observe(sentinel);
    return () => io.disconnect();
    // shown이 늘어도 바닥 표시가 계속 보이면 다시 관찰해서 화면을 채울 때까지 이어서 불러옴
  }, [auto, hasMore, sentinel, pageSize, shown]);

  return {
    shown,
    hasMore,
    /** 버튼을 보여 줄지 (아직 한 번도 안 눌렀을 때만) */
    showButton: hasMore && !auto,
    more,
    /** 자동 불러오기 중일 때 목록 맨 아래에 붙이는 표시 */
    sentinelRef: setSentinel,
    autoLoading: hasMore && auto,
  };
}
