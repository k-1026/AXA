import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSavedHospitals } from './savedHospitals';

// 납작한(평면) 하트 한 개: 찜 전에는 진한 선만, 찜하면 빨간색으로 꽉 채움 (SNS '좋아요' 방식, 2026-11-26)
const HEART =
  'M12 20.6s-7.4-4.5-9.2-9C1.5 8.3 3.5 4.6 7.1 4.6c2 0 3.6 1.1 4.9 2.9 1.3-1.8 2.9-2.9 4.9-2.9 3.6 0 5.6 3.7 4.3 7-1.8 4.5-9.2 9-9.2 9Z';

// 병원 찜 버튼. 찜할 때만 하트가 톡 커졌다가 제자리로 돌아온다
export function SaveHeart({ id, name }: { id: string; name: string }) {
  const { t } = useTranslation();
  const { isSaved, toggle } = useSavedHospitals();
  const [popping, setPopping] = useState(false);
  const saved = isSaved(id);

  return (
    <button
      type="button"
      className={`save-heart ${saved ? 'is-saved' : ''} ${popping ? 'is-popping' : ''}`}
      aria-pressed={saved}
      aria-label={`${t(saved ? 'mypage.saved.saved' : 'mypage.saved.save')}: ${name}`}
      onClick={() => {
        setPopping(!saved);
        toggle(id);
      }}
      onAnimationEnd={(e) => {
        if (e.target === e.currentTarget.firstElementChild) setPopping(false);
      }}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d={HEART} />
      </svg>
    </button>
  );
}
