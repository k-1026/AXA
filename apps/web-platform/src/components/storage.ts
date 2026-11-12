// 브라우저 저장소 읽기·쓰기. 사생활 보호 모드 등에서 막혀도 화면은 동작해야 하므로 실패는 무시한다
// 키는 모두 'medidaegu.' 로 시작
const PREFIX = 'medidaegu.';
const local = () => localStorage;
const session = () => sessionStorage;

function read(store: () => Storage, key: string): string | null {
  try {
    return store().getItem(PREFIX + key);
  } catch {
    return null;
  }
}

function write(store: () => Storage, key: string, value: string | null): void {
  try {
    if (value === null) store().removeItem(PREFIX + key);
    else store().setItem(PREFIX + key, value);
  } catch {
    // 저장 실패는 무시
  }
}

// 이 브라우저에 계속 남는 값 (localStorage): 언어·통화·로그인 토큰·계정별 찜 목록 등
export const readSetting = (key: string) => read(local, key);
export const writeSetting = (key: string, value: string) => write(local, key, value);
export const removeSetting = (key: string) => write(local, key, null);

// 이 탭에서만 유지되는 값 (sessionStorage): 데모 로그인
export const readSessionSetting = (key: string) => read(session, key);
export const writeSessionSetting = (key: string, value: string | null) => write(session, key, value);

/** 이름이 `@${suffix}`로 끝나는 저장 값을 모두 지운다 (탈퇴한 계정의 찜·방문 기록 등) */
export function removeSettingsWithSuffix(suffix: string): void {
  try {
    const keys: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k?.startsWith(PREFIX) && k.endsWith(`@${suffix}`)) keys.push(k);
    }
    keys.forEach((k) => localStorage.removeItem(k));
  } catch {
    // 저장소를 못 쓰면 지울 것도 없음
  }
}
