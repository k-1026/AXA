import { readSetting, removeSettingsWithSuffix, writeSetting } from './storage';

// 지금 화면을 쓰는 계정. 계정마다 따로 두는 데이터(대화·찜·방문 기록 등)의 열쇠로 쓴다
// - 'guest': 로그인 전 · 'demo': 데모 계정 · 'user:<id>': 실제 회원 (서버의 환자 id)
// 같은 탭에서 A가 로그아웃하고 B가 로그인해도 A의 데이터가 B에게 보이지 않게 한다
export type AccountKey = string;

export const accountKeyOf = (user: { id?: string; demo: boolean } | null): AccountKey =>
  !user ? 'guest' : user.demo ? 'demo' : `user:${user.id ?? ''}`;

let current: AccountKey = 'guest';
const changeListeners = new Set<() => void>();
const resetters = new Set<() => void>();

export const currentAccount = () => current;

/** AuthProvider가 로그인 상태가 바뀔 때 부른다 */
export function setCurrentAccount(key: AccountKey) {
  if (key === current) return;
  current = key;
  changeListeners.forEach((l) => l());
}

function onAccountChange(listener: () => void) {
  changeListeners.add(listener);
  return () => {
    changeListeners.delete(listener);
  };
}

/** 메모리에만 두는 데이터(대화·상담 등)를 지우는 함수를 등록. 로그아웃·탈퇴 때 모두 불린다 */
export function onAccountReset(reset: () => void) {
  resetters.add(reset);
}

/** 로그아웃·탈퇴·로그인 만료: 메모리에 둔 모든 계정 데이터를 지운다 */
export function resetAccountMemory() {
  resetters.forEach((r) => r());
}

/** 탈퇴: 이 브라우저에 남은 그 계정의 저장 값(찜·방문 기록 등)도 지운다 */
export function removeAccountData(key: AccountKey) {
  removeSettingsWithSuffix(key);
  resetAccountMemory();
}

/**
 * 계정별로 이 브라우저(localStorage)에 저장하는 목록. 키는 `<name>@<계정>`
 * useSyncExternalStore(list.subscribe, list.get)로 쓰면 계정이 바뀔 때 화면도 바뀐다
 */
export function createAccountList<T>(name: string) {
  const cache = new Map<AccountKey, T[]>();
  const listeners = new Set<() => void>();

  const get = (): T[] => {
    let items = cache.get(current);
    if (!items) {
      try {
        const parsed = JSON.parse(readSetting(`${name}@${current}`) ?? '[]');
        items = Array.isArray(parsed) ? (parsed as T[]) : [];
      } catch {
        items = [];
      }
      cache.set(current, items);
    }
    return items;
  };

  const set = (next: T[]) => {
    cache.set(current, next);
    writeSetting(`${name}@${current}`, JSON.stringify(next));
    listeners.forEach((l) => l());
  };

  const subscribe = (listener: () => void) => {
    listeners.add(listener);
    const off = onAccountChange(listener);
    return () => {
      listeners.delete(listener);
      off();
    };
  };

  // 탈퇴로 저장 값을 지웠을 때 메모리 사본도 버린다 (다음에 읽을 때 저장소에서 다시 읽음)
  onAccountReset(() => cache.clear());

  return { get, set, subscribe };
}
