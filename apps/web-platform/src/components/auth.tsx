import { createContext, useContext, useState, type ReactNode } from 'react';

// 로그인 상태. 실제 회원 기능(백엔드) 연결 전이라 지금은 "데모 계정"만 있다
// 데모 로그인은 이 탭에서만 유지 (sessionStorage), 탭을 닫으면 로그아웃
export interface User {
  name: string;
  demo: boolean; // true면 예시 데이터를 보여준다
}

const KEY = 'medidaegu.demoLogin';

function readDemo(): boolean {
  try {
    return sessionStorage.getItem(KEY) === '1';
  } catch {
    return false;
  }
}

function writeDemo(on: boolean) {
  try {
    if (on) sessionStorage.setItem(KEY, '1');
    else sessionStorage.removeItem(KEY);
  } catch {
    // 저장 실패는 무시 (새로고침하면 로그아웃 상태)
  }
}

const DEMO_USER: User = { name: 'Emma', demo: true };

const AuthContext = createContext<{
  user: User | null;
  loginDemo: () => void;
  logout: () => void;
}>({ user: null, loginDemo: () => {}, logout: () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => (readDemo() ? DEMO_USER : null));
  const loginDemo = () => {
    writeDemo(true);
    setUser(DEMO_USER);
  };
  const logout = () => {
    writeDemo(false);
    setUser(null);
  };
  return <AuthContext.Provider value={{ user, loginDemo, logout }}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
