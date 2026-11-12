// 백엔드 API 호출. 에러는 백엔드 형식 {code, message, detail}의 code로 구분 (docs/backend-contracts.md 4절)
const BASE = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string, // 'network'이면 서버에 연결 못 함
    public detail: Record<string, unknown> = {},
  ) {
    super(code);
  }
}

// 로그인 만료(401 auth.required) 때 부를 함수. AuthProvider가 등록해 로그아웃 처리한다 (화면마다 따로 처리하지 않게)
let onUnauthorized: ((token: string) => void) | null = null;
export const setUnauthorizedHandler = (fn: ((token: string) => void) | null) => {
  onUnauthorized = fn;
};

interface Options {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  token?: string | null;
}

export async function api<T>(path: string, { method = 'GET', body, token }: Options = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/api/v1${path}`, {
      method,
      headers: {
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'network');
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const err = new ApiError(res.status, data?.code ?? 'unknown', data?.detail ?? {});
    // 토큰을 보냈는데 로그인이 필요하다고 하면 만료·로그아웃된 토큰 (탈퇴 비밀번호 오류 401 auth.invalid_credentials는 제외)
    if (token && err.status === 401 && err.code === 'auth.required') onUnauthorized?.(token);
    throw err;
  }
  return data as T;
}
