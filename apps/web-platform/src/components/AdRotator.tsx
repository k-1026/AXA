import { useEffect, useMemo, useState } from 'react';
import { AdSlot } from './AdSlot';

/** wide: 두 칸 크기 배너 — 한 화면을 혼자 씀 */
export type Ad = { image: string; alt: string; href?: string; wide?: boolean };

const INTERVAL_MS = 5000;

// 광고를 두 칸 단위 화면으로 묶음: 두 칸 배너는 혼자, 한 칸 배너는 둘씩 (남으면 혼자)
function toPages(ads: Ad[]): Ad[][] {
  const pages: Ad[][] = [];
  let pair: Ad[] = [];
  for (const ad of ads) {
    if (ad.wide) {
      if (pair.length) { pages.push(pair); pair = []; }
      pages.push([ad]);
    } else {
      pair.push(ad);
      if (pair.length === 2) { pages.push(pair); pair = []; }
    }
  }
  if (pair.length) pages.push(pair);
  return pages;
}

// 광고 배너를 몇 초마다 두 칸 분량씩 넘김.
// 좁은 화면은 한 칸 배너 두 번째 자리를 숨김 (CSS). 두 칸 배너는 화면 너비 전체.
// 움직임 줄이기 설정이면 돌리지 않음. 마우스를 올리면 멈춤.
export function AdRotator({ ads }: { ads: Ad[] }) {
  const pages = useMemo(() => toPages(ads), [ads]);
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (pages.length < 2 || paused) return;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) return;
    const id = window.setInterval(() => setIndex((i) => (i + 1) % pages.length), INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [pages.length, paused]);

  if (pages.length === 0) return null;
  const page = pages[index % pages.length];

  return (
    <div
      className="ad-row ad-rotator"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      {page.map((ad, i) => (
        <AdSlot
          key={`${index}-${ad.image}`}
          className={`ad-fade${ad.wide ? ' ad-wide' : ''}${i === 1 ? ' ad-second' : ''}`}
          image={ad.image}
          alt={ad.alt}
          href={ad.href}
        />
      ))}
    </div>
  );
}
