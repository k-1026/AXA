import { useTranslation } from 'react-i18next';

// 광고 자리 (아직 광고 없음)
// docs/compliance.md: 광고는 목록·상세 옆에만, 건강·미용 카테고리 차단.
// 예약 요청서·동의·챗봇 화면에는 넣지 않는다.
export function AdSlot({ className = '' }: { className?: string }) {
  const { t } = useTranslation();
  return (
    <aside className={`ad-slot ${className}`} aria-label={t('ad.label')}>
      {t('ad.label')}
    </aside>
  );
}
