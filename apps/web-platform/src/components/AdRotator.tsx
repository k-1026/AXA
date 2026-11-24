import { useEffect, useState } from 'react';
import { AdSlot } from './AdSlot';

export type Ad = { image: string; alt: string; href?: string };

const INTERVAL_MS = 5000;

// 광고 배너 여러 개를 몇 초마다 돌려 보여줌.
// 넓은 화면은 두 자리(i, i+1), 좁은 화면은 한 자리만 (CSS에서 두 번째 자리를 숨김).
// 움직임 줄이기 설정이면 돌리지 않음. 마우스를 올리면 멈춤.
export function AdRotator({ ads }: { ads: Ad[] }) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (ads.length < 2 || paused) return;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) return;
    const id = window.setInterval(() => setIndex((i) => (i + 1) % ads.length), INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [ads.length, paused]);

  if (ads.length === 0) return null;
  const first = ads[index % ads.length];
  const second = ads[(index + 1) % ads.length];

  return (
    <div
      className="ad-row ad-rotator"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <AdSlot key={`a-${first.image}`} className="ad-fade" image={first.image} alt={first.alt} href={first.href} />
      {ads.length > 1 && (
        <AdSlot key={`b-${second.image}`} className="ad-fade ad-second" image={second.image} alt={second.alt} href={second.href} />
      )}
    </div>
  );
}
