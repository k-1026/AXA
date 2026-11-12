// 여러 화면에서 같이 쓰는 작은 도구 (예전에는 파일마다 같은 코드를 따로 두었음)
import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';

/** 화면 안에서만 쓰는 임시 id (서버 id 아님) */
export const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

/** 날짜·시간은 모두 한국 시간(KST) 기준 */
export const KST = 'Asia/Seoul';

/** 오늘 (YYYY-MM-DD, 한국 시간) */
export const todayKst = () => new Intl.DateTimeFormat('en-CA', { timeZone: KST }).format(new Date());

/** 한국어·영어는 꼭, 그 밖의 화면 언어(zh-TW·zh-CN·vi)는 있으면 쓰는 글. 사용자가 입력한 글은 문자열 그대로 */
export type KoEn = { ko: string; en: string; 'zh-TW'?: string; 'zh-CN'?: string; vi?: string };

/**
 * 화면 언어의 글이 있으면 그것, 없으면 영어 (병원 이름처럼 한국어·영어만 있는 데이터는 영어로). 문자열은 그대로
 * 언어가 바뀔 때만 새 함수 → useMemo 의존성으로 써도 됨
 */
export function useLocalized() {
  const { i18n } = useTranslation();
  const lang = i18n.language as keyof KoEn;
  return useCallback((x: string | KoEn): string => (typeof x === 'string' ? x : x[lang] ?? x.en), [lang]);
}

/** 검색용 글: 한국어·영어를 모두 넣어 어느 언어로 찾아도 걸리게 */
export const searchText = (x?: string | KoEn) => (!x ? '' : typeof x === 'string' ? x : `${x.ko} ${x.en}`);
