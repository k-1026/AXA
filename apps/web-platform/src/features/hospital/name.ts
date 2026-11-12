import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import type { KoEn } from '../../lib/common';
import { localAddress, localHospitalName } from './localize';
import type { Hospital } from './types';

// 한국어는 원래 이름, 영어는 영어 이름, 중국어·베트남어는 진료과·기관 종류를 번역한 이름 (localize.ts)
// 언어가 바뀔 때만 새 함수 → useMemo 의존성으로 써도 매번 다시 계산하지 않음
export function useHospitalName() {
  const { i18n } = useTranslation();
  const lang = i18n.language;
  return useCallback((h: Hospital) => (lang === 'ko' ? h.name : localHospitalName(h.nameEn, lang)), [lang]);
}

/** 주소를 화면 언어로 (한국어 화면은 원문) */
export function useHospitalAddress() {
  const { i18n } = useTranslation();
  const lang = i18n.language;
  return useCallback((h: Hospital) => localAddress(h.addr, lang), [lang]);
}

/** 찜·상담처럼 이름을 저장해 두는 곳에서 쓰는 5개 언어 이름 */
export const hospitalNames = (h: Hospital): KoEn => ({
  ko: h.name,
  en: h.nameEn,
  'zh-TW': localHospitalName(h.nameEn, 'zh-TW'),
  'zh-CN': localHospitalName(h.nameEn, 'zh-CN'),
  vi: localHospitalName(h.nameEn, 'vi'),
});

// https://www.instagram.com/abc/ → @abc
export const instagramHandle = (url: string) =>
  url.replace(/^https?:\/\/(www\.)?instagram\.com\//, '@').replace(/\/$/, '');
