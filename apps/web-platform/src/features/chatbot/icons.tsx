// 챗봇 화면 아이콘 (선 아이콘, currentColor 사용)
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

/** 메디 챗봇 얼굴 (말풍선 + 눈 두 개) */
// 챗봇 캐릭터 (별 모양). 장식이라 alt는 비워 둔다
export function BotIcon() {
  return <img className="chat-bot-icon" src="/chatbot/medi-star-doctor.webp" alt="" />;
}

const icon = (d: string | string[]) =>
  function Icon() {
    return (
      <svg {...base}>
        {(Array.isArray(d) ? d : [d]).map((p) => (
          <path key={p} d={p} />
        ))}
      </svg>
    );
  };

export const PlusIcon = icon('M12 5v14M5 12h14');
export const SearchIcon = icon(['M10.5 4a6.5 6.5 0 1 1 0 13 6.5 6.5 0 0 1 0-13Z', 'm15.5 15.5 5 5']);
export const MenuIcon = icon('M4 7h16M4 12h16M4 17h16');
export const CloseIcon = icon('M6 6l12 12M18 6 6 18');
export const SendIcon = icon(['M12 19V5', 'm6 11 6-6 6 6']);
export const CopyIcon = icon(['M9 9h10v10H9z', 'M5 15V5h10']);
export const ThumbIcon = icon([
  'M7 11v9H4v-9h3Z',
  'M7 11l4-7c1.3 0 2.2 1 2 2.3L12.6 10H18a2 2 0 0 1 2 2.3l-1.1 6A2 2 0 0 1 17 20H7',
]);
export const InfoIcon = icon(['M12 3.5a8.5 8.5 0 1 1 0 17 8.5 8.5 0 0 1 0-17Z', 'M12 11v5M12 8h.01']);
export const GearIcon = icon([
  'M12 9a3 3 0 1 1 0 6 3 3 0 0 1 0-6Z',
  'M19 12a7 7 0 0 0-.1-1.2l2-1.5-2-3.4-2.3 1a7 7 0 0 0-2-1.2L14.3 3h-4l-.3 2.6a7 7 0 0 0-2 1.2l-2.4-1-2 3.4 2 1.6A7 7 0 0 0 5.6 12c0 .4 0 .8.1 1.2l-2 1.5 2 3.4 2.3-1a7 7 0 0 0 2 1.2l.3 2.6h4l.3-2.6a7 7 0 0 0 2-1.2l2.4 1 2-3.4-2-1.5c.1-.4.1-.8.1-1.2Z',
]);

// 하단 빠른 메뉴
export const HospitalIcon = icon(['M5 20V6h14v14', 'M3 20h18', 'M12 9v5M9.5 11.5h5', 'M10 20v-3h4v3']);
export const CoinsIcon = icon([
  'M9 6c3 0 5.5-.9 5.5-2S12 2 9 2 3.5 2.9 3.5 4 6 6 9 6Z',
  'M3.5 4v8c0 1.1 2.5 2 5.5 2',
  'M3.5 8c0 1.1 2.5 2 5.5 2',
  'M15 12c3 0 5.5-.9 5.5-2S18 8 15 8s-5.5.9-5.5 2S12 12 15 12Z',
  'M9.5 10v8c0 1.1 2.5 2 5.5 2s5.5-.9 5.5-2v-8',
  'M9.5 14c0 1.1 2.5 2 5.5 2s5.5-.9 5.5-2',
]);
export const TranslateIcon = icon(['M4 5h8M8 3v2M6 5c.5 3 2.5 5.5 5 7', 'M10 5c-.5 3-2.5 5.5-6 7', 'm12 21 4-9 4 9M13.5 18h5']);
export const PinIcon = icon(['M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11Z', 'M12 7.7a2.3 2.3 0 1 1 0 4.6 2.3 2.3 0 0 1 0-4.6Z']);

export function MoreIcon() {
  return (
    <svg {...base} fill="currentColor" stroke="none">
      <circle cx="5" cy="12" r="1.7" />
      <circle cx="12" cy="12" r="1.7" />
      <circle cx="19" cy="12" r="1.7" />
    </svg>
  );
}
