import { useState } from 'react';
import { useTranslation } from 'react-i18next';

// 병원 대표사진. 없거나 불러오지 못하면 "대표사진 없음"
// 사진은 외부 주소라 어느 페이지에서 왔는지 보내지 않는다 (no-referrer)
export function HospitalPhoto({ src, className = '' }: { src?: string; className?: string }) {
  const { t } = useTranslation();
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return <div className={`hospital-photo is-empty ${className}`}>{t('hospital.noPhoto')}</div>;
  }

  return (
    <div className={`hospital-photo ${className}`} aria-hidden="true">
      <img src={src} alt="" loading="lazy" decoding="async" referrerPolicy="no-referrer" onError={() => setFailed(true)} />
    </div>
  );
}
