import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import i18n from '../i18n';
import { api, ApiError, setUnauthorizedHandler } from './api';
import { accountKeyOf, removeAccountData, resetAccountMemory, setCurrentAccount, type AccountKey } from './account';
import { readSessionSetting, readSetting, removeSetting, writeSessionSetting, writeSetting } from './storage';

// 로그인 상태
// - 실제 회원: 백엔드 회원가입·로그인. 토큰은 이 브라우저(localStorage)에 두고, 로그아웃하면 서버 세션도 끝냄
// - 데모 계정: 발표·화면 확인용. 이 탭에서만 유지 (sessionStorage), 예시 데이터를 보여준다
export interface User {
  id?: string; // 실제 회원의 서버 id (계정별 데이터를 나누는 데 씀). 데모는 없음
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
  id: string;
  email: string;
  display_name: string | null;
  preferred_lang: string;
}

const DEMO_KEY = 'demoLogin';
const TOKEN_KEY = 'token';
const DEMO_USER: User = { name: 'Emma', demo: true };

function toUser(me: Me): User {
  return { id: me.id, name: me.display_name || me.email.split('@')[0], demo: false, email: me.email };
}

const AuthContext = createContext<{
  user: User | null;
  account: AccountKey; // 계정별 데이터의 열쇠 ('guest' | 'demo' | 'user:<id>')
  token: string | null; // 실제 회원의 API 토큰 (데모·비로그인은 null)
  ready: boolean; // 저장된 토큰 확인이 끝났는지
  loginDemo: () => void;
  login: (email: string, password: string) => Promise<void>;
  signup: (input: SignupInput) => Promise<void>;
  withdraw: (password: string) => Promise<void>;
  logout: () => void;
}>({
  user: null,
  account: 'guest',
  token: null,
  ready: true,
  loginDemo: () => {},
  login: async () => {},
  signup: async () => {},
  withdraw: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => readSetting(TOKEN_KEY));
  const [user, setUser] = useState<User | null>(() => (readSessionSetting(DEMO_KEY) === '1' ? DEMO_USER : null));
  const [ready, setReady] = useState(() => !readSetting(TOKEN_KEY));
  const account = accountKeyOf(user);

  // 계정별 저장소(찜·방문 기록 등)가 화면을 그리기 전에 새 계정으로 바뀌게 (useLayoutEffect)
  useLayoutEffect(() => setCurrentAccount(account), [account]);

  const clearToken = useCallback(() => {
    removeSetting(TOKEN_KEY);
    setToken(null);
  }, []);

  // 로그인 만료: 어느 API에서든 401 auth.required가 오면 로그아웃 (지금 토큰일 때만 — 이전 계정의 늦은 응답은 무시)
  const tokenRef = useRef(token);
  tokenRef.current = token;
  useEffect(() => {
    setUnauthorizedHandler((used) => {
      if (used !== tokenRef.current) return;
      clearToken();
      resetAccountMemory();
      setUser(null);
    });
    return () => setUnauthorizedHandler(null);
  }, [clearToken]);

  // 저장된 토큰이 아직 유효한지 서버에 확인 (로그아웃·만료됐으면 지움)
  useEffect(() => {
    if (!token) return;
    let alive = true;
    api<Me>('/me', { token })
      .then((me) => alive && setUser(toUser(me)))
      .catch((e) => {
        // auth.required는 위의 공통 처리가 로그아웃한다. 그 밖의 401도 토큰을 지움
        if (alive && e instanceof ApiError && e.status === 401) clearToken();
      })
      .finally(() => alive && setReady(true));
    return () => {
      alive = false;
    };
  }, [token, clearToken]);

  const startSession = async (accessToken: string) => {
    const me = await api<Me>('/me', { token: accessToken });
    resetAccountMemory(); // 앞 계정(데모 포함)의 메모리 데이터를 남기지 않음
    writeSessionSetting(DEMO_KEY, null);
    writeSetting(TOKEN_KEY, accessToken);
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
    resetAccountMemory();
    writeSessionSetting(DEMO_KEY, '1');
    setUser(DEMO_USER);
  };

  const logout = () => {
    if (token) api('/auth/patient/logout', { method: 'POST', token }).catch(() => {});
    clearToken();
    writeSessionSetting(DEMO_KEY, null);
    resetAccountMemory(); // 같은 탭에서 다음에 로그인한 사람에게 대화·상담이 보이지 않게
    setUser(null);
  };

  // 탈퇴: 비밀번호 확인 후 서버에서 계정 삭제 표시 + 모든 기기 로그아웃 → 이 브라우저도 로그아웃
  const withdraw = async (password: string) => {
    await api('/me', { method: 'DELETE', token, body: { password } });
    clearToken();
    removeAccountData(account); // 이 브라우저에 남은 이 계정의 찜·방문 기록 + 메모리 데이터
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, account, token: user && !user.demo ? token : null, ready, loginDemo, login, signup, withdraw, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
