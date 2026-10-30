// 언어·통화 같은 개인 설정만 저장. 사생활 보호 모드 등에서 막혀도 화면은 동작해야 함
export function readSetting(key: string): string | null {
  try {
    return localStorage.getItem(`medidaegu.${key}`);
  } catch {
    return null;
  }
}

export function writeSetting(key: string, value: string): void {
  try {
    localStorage.setItem(`medidaegu.${key}`, value);
  } catch {
    // 저장 실패는 무시
  }
}
