import { readSessionSetting, writeSessionSetting } from '../../components/storage';

// 병원 관계자(직원) 토큰. 환자 로그인 토큰과 따로, 이 탭(sessionStorage)에만 둔다 — 탭을 닫으면 사라짐
// /dashboard 화면 진입만 막는 용도. 실제 권한(병원 API)은 백엔드가 토큰으로 확인한다
const KEY = 'staffToken';

export const readStaffToken = () => readSessionSetting(KEY);
export const saveStaffToken = (token: string) => writeSessionSetting(KEY, token);
export const clearStaffToken = () => writeSessionSetting(KEY, null);
