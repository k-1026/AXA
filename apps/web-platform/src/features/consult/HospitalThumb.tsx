import { useState } from 'react';
import { HospitalIcon } from '../chatbot/icons';

// 상담 목록·머리말의 작은 병원 사진. 사진이 없으면 병원 아이콘
export function HospitalThumb({ photo, size = 'sm' }: { photo?: string; size?: 'sm' | 'lg' }) {
  const [failed, setFailed] = useState(false);
  return (
    <span className={`consult-thumb is-${size}`} aria-hidden="true">
      {photo && !failed ? (
        <img src={photo} alt="" loading="lazy" referrerPolicy="no-referrer" onError={() => setFailed(true)} />
      ) : (
        <HospitalIcon />
      )}
    </span>
  );
}
