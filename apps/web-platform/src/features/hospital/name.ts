import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import type { KoEn } from '../../lib/common';
import { localAddress, localHospitalName } from './localize';
import type { Hospital } from './types';

// 시연용 가상 병원 이름 뒤에 붙는 표시 (실제 병원과 헷갈리지 않게, 이름이 보이는 모든 곳에 같이 나옴)
const DEMO_SUFFIX: Record<string, string> = {
  ko: ' (가상 · 시연용)',
  en: ' (Demo · not a real clinic)',
  'zh-TW': '（虛擬 · 示範用）',
  'zh-CN': '（虚拟 · 演示用）',
  vi: ' (Ảo · dùng để minh họa)',
  ja: '（架空 · デモ用）',
};
const nameIn = (h: Hospital, lang: string) =>
  (lang === 'ko' ? h.name : localHospitalName(h.nameEn, lang)) + (h.demo ? DEMO_SUFFIX[lang] ?? DEMO_SUFFIX.en : '');

// 한국어는 원래 이름, 영어는 영어 이름, 중국어·베트남어·일본어는 진료과·기관 종류를 번역한 이름 (localize.ts)
// 언어가 바뀔 때만 새 함수 → useMemo 의존성으로 써도 매번 다시 계산하지 않음
export function useHospitalName() {
  const { i18n } = useTranslation();
  const lang = i18n.language;
  return useCallback((h: Hospital) => nameIn(h, lang), [lang]);
}

/** 주소를 화면 언어로 (한국어 화면은 원문) */
export function useHospitalAddress() {
  const { i18n } = useTranslation();
  const lang = i18n.language;
  return useCallback((h: Hospital) => localAddress(h.addr, lang), [lang]);
}

/** 찜·상담처럼 이름을 저장해 두는 곳에서 쓰는 6개 언어 이름 */
export const hospitalNames = (h: Hospital): KoEn => ({
  ko: nameIn(h, 'ko'),
  en: nameIn(h, 'en'),
  'zh-TW': nameIn(h, 'zh-TW'),
  'zh-CN': nameIn(h, 'zh-CN'),
  vi: nameIn(h, 'vi'),
  ja: nameIn(h, 'ja'),
});

// https://www.instagram.com/abc/ → @abc
export const instagramHandle = (url: string) =>
  url.replace(/^https?:\/\/(www\.)?instagram\.com\//, '@').replace(/\/$/, '');
