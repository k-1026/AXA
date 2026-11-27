import { readSessionSetting, writeSessionSetting } from '../../components/storage';

// 병원 관계자(직원) 토큰. 환자 로그인 토큰과 따로, 이 탭(sessionStorage)에만 둔다 — 탭을 닫으면 사라짐
// /dashboard 화면 진입만 막는 용도. 실제 권한(병원 API)은 백엔드가 토큰으로 확인한다
const KEY = 'staffToken';

export const readStaffToken = () => readSessionSetting(KEY);
export const saveStaffToken = (token: string) => writeSessionSetting(KEY, token);
export const clearStaffToken = () => writeSessionSetting(KEY, null);

// 로컬 개발 미리보기: /dashboard?preview=1 → 로그인 없이 대시보드 화면을 봄 (토큰이 없으니 병원 API는 부르지 않고 예시 데이터만 보임)
// 개발 서버(npm run dev)에서만 켜짐 — 배포 사이트에서는 무시
const PREVIEW = 'staffPreview';
export const isStaffPreview = () => {
  if (!import.meta.env.DEV) return false;
  if (new URLSearchParams(window.location.search).get('preview') === '1') writeSessionSetting(PREVIEW, '1');
  return readSessionSetting(PREVIEW) === '1';
};
