import { useTranslation } from 'react-i18next';
import type { Hospital } from './types';

// 한국어는 원래 이름, 그 밖의 언어는 모두 영어 이름으로 통일
export function useHospitalName() {
  const { i18n } = useTranslation();
  return (h: Hospital) => (i18n.language === 'ko' ? h.name : h.nameEn);
}
