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
// 시연용 가상 병원의 중국어·일본어·베트남어 이름 (docs/번역-표기-기준.md 2-5)
// '예시'는 뜻이 있는 말이라 번역하고, 구 이름(수성·달서)은 한자 언어에서 한자, 도로 이름(동성로)은 알파벳
const DEMO_NAMES: Record<string, Partial<Record<string, string>>> = {
  'DEMO-9001': { 'zh-TW': '範例皮膚科診所', 'zh-CN': '示例皮肤科诊所', ja: 'サンプル皮膚科クリニック', vi: 'Phòng khám Da liễu Mẫu' },
  'DEMO-9002': { 'zh-TW': '範例壽城皮膚科診所', 'zh-CN': '示例寿城皮肤科诊所', ja: 'サンプル寿城皮膚科クリニック', vi: 'Phòng khám Da liễu Mẫu Suseong' },
  'DEMO-9003': { 'zh-TW': '範例 Dongseongno 整形外科診所', 'zh-CN': '示例 Dongseongno 整形外科诊所', ja: 'サンプル Dongseongno 形成外科クリニック', vi: 'Phòng khám Thẩm mỹ Mẫu Dongseongno' },
  'DEMO-9004': { 'zh-TW': '範例達西眼科診所', 'zh-CN': '示例达西眼科诊所', ja: 'サンプル達西眼科クリニック', vi: 'Phòng khám Mắt Mẫu Dalseo' },
};
const baseName = (h: Hospital, lang: string) =>
  lang === 'ko' ? h.name : (h.demo && DEMO_NAMES[h.id]?.[lang]) || localHospitalName(h.nameEn, lang);
const nameIn = (h: Hospital, lang: string) => baseName(h, lang) + (h.demo ? DEMO_SUFFIX[lang] ?? DEMO_SUFFIX.en : '');

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
