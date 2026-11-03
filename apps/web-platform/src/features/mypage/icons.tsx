// 마이페이지 아이콘 (선 아이콘, currentColor 사용)
const base = {
  width: 24,
  height: 24,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
};

export function HospitalHeartIcon() {
  return (
    <svg {...base}>
      <path d="M4 21V8h5V4h6v4" />
      <path d="M11 6.5v3M9.5 8h3" />
      <path d="M2.5 21h11" />
      <path d="M7 12h1M7 15.5h1M7 19h1" />
      <path d="M17 21s-4.5-2.7-4.5-5.6A2.4 2.4 0 0 1 17 14a2.4 2.4 0 0 1 4.5 1.4C21.5 18.3 17 21 17 21Z" />
    </svg>
  );
}

export function CalendarCheckIcon() {
  return (
    <svg {...base}>
      <rect x="3.5" y="5" width="17" height="15.5" rx="2.5" />
      <path d="M3.5 10h17M8 3v4M16 3v4" />
      <path d="m9 15 2 2 4-4" />
    </svg>
  );
}

export function HistoryIcon() {
  return (
    <svg {...base}>
      <path d="M3.5 12a8.5 8.5 0 1 0 2.5-6" />
      <path d="M3.5 4v4h4" />
      <path d="M12 7.5V12l3 2" />
    </svg>
  );
}

export function CalendarIcon() {
  return (
    <svg {...base}>
      <rect x="3.5" y="5" width="17" height="15.5" rx="2" />
      <path d="M3.5 10h17M8 3v4M16 3v4" />
      <path d="M7.5 13.5h1M11.5 13.5h1M15.5 13.5h1M7.5 17h1M11.5 17h1" />
    </svg>
  );
}

export function ClockIcon() {
  return (
    <svg {...base}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </svg>
  );
}

export function PencilIcon() {
  return (
    <svg {...base}>
      <path d="m4 20 1-4L16 5l3 3L8 19l-4 1Z" />
      <path d="m14 7 3 3" />
    </svg>
  );
}

export function PlusIcon() {
  return (
    <svg {...base}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function GearIcon() {
  return (
    <svg {...base}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z" />
    </svg>
  );
}

export function ChevronRightIcon() {
  return (
    <svg {...base}>
      <path d="m9 6 6 6-6 6" />
    </svg>
  );
}

export function ArrowRightIcon() {
  return (
    <svg {...base}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

export function ArrowUpRightIcon() {
  return (
    <svg {...base}>
      <path d="M7 17 17 7M8 7h9v9" />
    </svg>
  );
}

export function MoreIcon() {
  return (
    <svg {...base} fill="currentColor" stroke="none">
      <circle cx="5" cy="12" r="1.6" />
      <circle cx="12" cy="12" r="1.6" />
      <circle cx="19" cy="12" r="1.6" />
    </svg>
  );
}

export function CheckIcon() {
  return (
    <svg {...base} strokeWidth={2.6}>
      <path d="m5 12.5 4.5 4.5L19 7.5" />
    </svg>
  );
}

// 일정 카드 오른쪽 위 장식 그림 (산·도심·83타워·꽃나무)
export function DaeguSkyline() {
  return (
    <svg className="skyline" viewBox="0 0 360 100" aria-hidden="true" preserveAspectRatio="xMaxYMax slice">
      <path d="M0 100 C40 70 70 62 110 70 S170 50 210 58 S290 44 360 56 V100 Z" fill="#cfe0f1" />
      <path d="M60 100 C100 78 140 74 180 80 S260 66 360 74 V100 Z" fill="#b9d3ea" />
      <g fill="#9cbfe0">
        <rect x="120" y="68" width="10" height="32" />
        <rect x="134" y="60" width="12" height="40" />
        <rect x="150" y="72" width="9" height="28" />
        <rect x="246" y="58" width="12" height="42" />
        <rect x="262" y="66" width="10" height="34" />
        <rect x="300" y="62" width="14" height="38" />
        <rect x="318" y="70" width="10" height="30" />
      </g>
      <g fill="#7ea8d3">
        <rect x="176" y="64" width="11" height="36" />
        <rect x="226" y="70" width="12" height="30" />
        <rect x="282" y="56" width="11" height="44" />
      </g>
      {/* 83타워 */}
      <g fill="#6b93c4">
        <rect x="205.5" y="30" width="3" height="70" />
        <path d="M201 44h12l-2 7h-8z" />
        <rect x="206.5" y="10" width="1" height="20" />
      </g>
      <g fill="#7cbf8a">
        <circle cx="96" cy="94" r="10" />
        <circle cx="114" cy="96" r="8" />
        <circle cx="166" cy="95" r="9" />
        <circle cx="240" cy="96" r="9" />
        <circle cx="270" cy="95" r="10" />
        <circle cx="330" cy="94" r="10" />
      </g>
      <g fill="#f3b7c8">
        <circle cx="344" cy="88" r="9" />
        <circle cx="352" cy="94" r="7" />
        <circle cx="194" cy="94" r="7" />
      </g>
    </svg>
  );
}
