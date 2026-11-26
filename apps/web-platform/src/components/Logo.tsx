// 메디대구 로고 v8 (2026-11-20 팀 확정): MD 모노그램 + 청진판 고리, MEDI / DAEGU 두 줄
// 원본: research-data 브랜치 marketing/instagram/src/make_logo_v8.py (선 굵기 24, 같은 좌표)
// 색은 currentColor → 부모의 color(브랜드 파랑)를 따라감

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 336 276" aria-hidden="true" focusable="false">
      <g fill="none" stroke="currentColor" strokeWidth="24" strokeLinejoin="round" strokeLinecap="butt">
        <path d="M24 228V24l72 84 72-84v180" />
        <path d="M168 24h42a102 102 0 0 1 0 204h-18" />
        <circle cx="168" cy="228" r="24" />
      </g>
    </svg>
  );
}

export function Logo() {
  return (
    <span className="md-logo">
      <LogoMark className="md-logo-mark" />
      <span className="md-logo-word" aria-hidden="true">
        <span className="md-logo-medi">MEDI</span>
        <span className="md-logo-daegu">DAEGU</span>
      </span>
      <span className="visually-hidden">MediDaegu</span>
    </span>
  );
}
