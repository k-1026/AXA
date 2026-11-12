import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import ko from './locales/ko.json';
import en from './locales/en.json';
import zhCN from './locales/zh-CN.json';
import zhTW from './locales/zh-TW.json';
import vi from './locales/vi.json';
import { readSetting, writeSetting } from '../components/storage';

// UI 언어: 한국어 + plan.md 9절 제안 4개 (영어·간체·번체·베트남어)
export const LANGUAGES = [
  { code: 'ko', label: '한국어' },
  { code: 'en', label: 'English' },
  { code: 'zh-CN', label: '简体中文' },
  { code: 'zh-TW', label: '繁體中文' },
  { code: 'vi', label: 'Tiếng Việt' },
] as const;

const resources = {
  ko: { translation: ko },
  en: { translation: en },
  'zh-CN': { translation: zhCN },
  'zh-TW': { translation: zhTW },
  vi: { translation: vi },
};

// 저장된 선택 → 브라우저 언어 → 영어 순서
function detectLanguage(): string {
  const saved = readSetting('lang');
  if (saved && saved in resources) return saved;
  for (const lang of navigator.languages ?? [navigator.language]) {
    if (lang in resources) return lang;
    if (lang.startsWith('zh')) return /TW|HK|Hant/i.test(lang) ? 'zh-TW' : 'zh-CN';
    const base = lang.split('-')[0];
    if (base in resources) return base;
  }
  return 'en';
}

i18n.use(initReactI18next).init({
  resources,
  lng: detectLanguage(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
});

i18n.on('languageChanged', (lang) => {
  writeSetting('lang', lang);
  document.documentElement.lang = lang;
});
document.documentElement.lang = i18n.language;

export default i18n;
