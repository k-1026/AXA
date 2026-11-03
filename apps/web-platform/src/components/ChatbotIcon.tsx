import { useId } from 'react';

// 헤더 챗봇 아이콘: 그라데이션 말풍선 + 눈 2개
export function ChatbotIcon({ size = 28 }: { size?: number }) {
  const id = useId();
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <defs>
        <linearGradient id={`${id}-ring`} x1="4" y1="28" x2="28" y2="4" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#2f6bff" />
          <stop offset="0.45" stopColor="#8b3dff" />
          <stop offset="0.75" stopColor="#ff4f8b" />
          <stop offset="1" stopColor="#ff9a2e" />
        </linearGradient>
        <linearGradient id={`${id}-eye`} x1="0" y1="12" x2="0" y2="19" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#7b4dff" />
          <stop offset="1" stopColor="#2f6bff" />
        </linearGradient>
      </defs>
      {/* 둥근 말풍선, 꼬리는 왼쪽 아래 */}
      <path
        d="M16 4.5c6.4 0 11.5 5 11.5 11.2S22.4 27 16 27H5.5a.8.8 0 0 1-.6-1.3l2-2.6A11 11 0 0 1 4.5 15.7C4.5 9.5 9.6 4.5 16 4.5Z"
        stroke={`url(#${id}-ring)`}
        strokeWidth="3"
        strokeLinejoin="round"
      />
      <rect x="11.2" y="12" width="3" height="7" rx="1.5" fill={`url(#${id}-eye)`} />
      <rect x="17.8" y="12" width="3" height="7" rx="1.5" fill={`url(#${id}-eye)`} />
    </svg>
  );
}
