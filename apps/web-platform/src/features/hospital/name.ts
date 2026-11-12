import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import type { Hospital } from './types';

// 한국어는 원래 이름, 그 밖의 언어는 모두 영어 이름으로 통일
// 언어가 바뀔 때만 새 함수 → useMemo 의존성으로 써도 매번 다시 계산하지 않음
export function useHospitalName() {
  const { i18n } = useTranslation();
  const ko = i18n.language === 'ko';
  return useCallback((h: Hospital) => (ko ? h.name : h.nameEn), [ko]);
}

// https://www.instagram.com/abc/ → @abc
export const instagramHandle = (url: string) =>
  url.replace(/^https?:\/\/(www\.)?instagram\.com\//, '@').replace(/\/$/, '');
