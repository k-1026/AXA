import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import i18n from '../i18n';
import { api, ApiError } from './api';

// 로그인 상태
// - 실제 회원: 백엔드 회원가입·로그인. 토큰은 이 브라우저(localStorage)에 두고, 로그아웃하면 서버 세션도 끝냄
// - 데모 계정: 발표·화면 확인용. 이 탭에서만 유지 (sessionStorage), 예시 데이터를 보여준다
export interface User {
  name: string;
  demo: boolean; // true면 예시 데이터를 보여준다
  email?: string;
}

export interface SignupInput {
  email: string;
  password: string;
  display_name: string | null;
  preferred_lang: string;
  timezone: string;
  age14_confirmed: boolean;
  consents: { kind: 'terms' | 'privacy'; version: string }[];
}

interface Me {
  email: string;
  display_name: string | null;
  preferred_lang: string;
}

const DEMO_KEY = 'medidaegu.demoLogin';
const TOKEN_KEY = 'medidaegu.token';
const DEMO_USER: User = { name: 'Emma', demo: true };

function read(store: () => Storage, key: string): string | null {
  try {
    return store().getItem(key);
  } catch {
    return null;
  }
}

function write(store: () => Storage, key: string, value: string | null) {
  try {
    if (value === null) store().removeItem(key);
    else store().setItem(key, value);
  } catch {
    // 저장 실패는 무시 (새로고침하면 로그아웃 상태)
  }
}

const local = () => localStorage;
const session = () => sessionStorage;

function toUser(me: Me): User {
  return { name: me.display_name || me.email.split('@')[0], demo: false, email: me.email };
}

const AuthContext = createContext<{
  user: User | null;
  token: string | null; // 실제 회원의 API 토큰 (데모·비로그인은 null)
  ready: boolean; // 저장된 토큰 확인이 끝났는지
  loginDemo: () => void;
  login: (email: string, password: string) => Promise<void>;
  signup: (input: SignupInput) => Promise<void>;
  withdraw: (password: string) => Promise<void>;
  logout: () => void;
}>({
  user: null,
  token: null,
  ready: true,
  loginDemo: () => {},
  login: async () => {},
  signup: async () => {},
  withdraw: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => read(local, TOKEN_KEY));
  const [user, setUser] = useState<User | null>(() =>
    read(session, DEMO_KEY) === '1' ? DEMO_USER : null,
  );
  const [ready, setReady] = useState(() => !read(local, TOKEN_KEY));

  const clearToken = useCallback(() => {
    write(local, TOKEN_KEY, null);
    setToken(null);
  }, []);

  // 저장된 토큰이 아직 유효한지 서버에 확인 (로그아웃·만료됐으면 지움)
  useEffect(() => {
    if (!token) return;
    let alive = true;
    api<Me>('/me', { token })
      .then((me) => alive && setUser(toUser(me)))
      .catch((e) => {
        if (alive && e instanceof ApiError && e.status === 401) clearToken();
      })
      .finally(() => alive && setReady(true));
    return () => {
      alive = false;
    };
  }, [token, clearToken]);

  const startSession = async (accessToken: string) => {
    const me = await api<Me>('/me', { token: accessToken });
    write(session, DEMO_KEY, null);
    write(local, TOKEN_KEY, accessToken);
    setToken(accessToken);
    setUser(toUser(me));
    if (me.preferred_lang && me.preferred_lang !== i18n.language) i18n.changeLanguage(me.preferred_lang);
  };

  const login = async (email: string, password: string) => {
    const r = await api<{ access_token: string }>('/auth/patient/login', {
      method: 'POST',
      body: { email, password },
    });
    await startSession(r.access_token);
  };

  const signup = async (input: SignupInput) => {
    const r = await api<{ access_token: string }>('/auth/patient/signup', {
      method: 'POST',
      body: input,
    });
    await startSession(r.access_token);
  };

  const loginDemo = () => {
    write(session, DEMO_KEY, '1');
    setUser(DEMO_USER);
  };

  const logout = () => {
    if (token) api('/auth/patient/logout', { method: 'POST', token }).catch(() => {});
    clearToken();
    write(session, DEMO_KEY, null);
    setUser(null);
  };

  // 탈퇴: 비밀번호 확인 후 서버에서 계정 삭제 표시 + 모든 기기 로그아웃 → 이 브라우저도 로그아웃
  const withdraw = async (password: string) => {
    await api('/me', { method: 'DELETE', token, body: { password } });
    clearToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token: user && !user.demo ? token : null, ready, loginDemo, login, signup, withdraw, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
