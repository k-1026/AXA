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
  if (!res.ok) throw new ApiError(res.status, data?.code ?? 'unknown', data?.detail ?? {});
  return data as T;
}
