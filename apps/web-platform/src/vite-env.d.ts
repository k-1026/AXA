/// <reference types="vite/client" />

interface ImportMetaEnv {
  // 백엔드 주소. 없으면 로컬 개발 서버 (http://localhost:8000)
  readonly VITE_API_URL?: string;
}
