import { useId, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSavedHospitals } from './savedHospitals';

const HEART = 'M12 20.5s-8-4.9-8-10.7A4.5 4.5 0 0 1 12 7a4.5 4.5 0 0 1 8 2.8c0 5.8-8 10.7-8 10.7Z';

// 병원 찜 버튼. 찜할 때만 하트가 떠올랐다가 아래부터 색이 차오른다
export function SaveHeart({ id, name }: { id: string; name: string }) {
  const { t } = useTranslation();
  const { isSaved, toggle } = useSavedHospitals();
  const [popping, setPopping] = useState(false);
  const saved = isSaved(id);
  const gradientId = `save-heart-fill-${useId()}`; // 카드마다 SVG id가 겹치지 않게

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
        <defs>
          <linearGradient id={gradientId} x1="0.2" y1="0" x2="0.8" y2="1">
            <stop offset="0" stopColor="#fb7185" />
            <stop offset="1" stopColor="#e11d48" />
          </linearGradient>
        </defs>
        <path className="save-heart-color" d={HEART} fill={`url(#${gradientId})`} />
        <path className="save-heart-shine" d="M7.4 9.6a2.3 2.3 0 0 1 1.9-2" />
        <path className="save-heart-line" d={HEART} />
      </svg>
    </button>
  );
}
