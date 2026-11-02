import { useTranslation } from 'react-i18next';

// 광고 자리. image가 없으면 빈 자리 표시
// docs/compliance.md: 광고는 목록·상세 옆에만, 건강·미용 카테고리 차단.
// 예약 요청서·동의·챗봇 화면에는 넣지 않는다.
export function AdSlot({
  className = '',
  image,
  alt = '',
}: {
  className?: string;
  image?: string;
  alt?: string;
}) {
  const { t } = useTranslation();
  return (
    <aside className={`ad-slot ${image ? 'has-image' : ''} ${className}`} aria-label={t('ad.label')}>
      {image ? <img src={image} alt={alt} /> : t('ad.label')}
    </aside>
  );
}
