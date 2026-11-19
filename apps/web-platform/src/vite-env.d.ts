/// <reference types="vite/client" />

interface ImportMetaEnv {
  // 백엔드 주소. 없으면 로컬 개발 서버 (http://localhost:8000)
  readonly VITE_API_URL?: string;
  // 병원 대시보드 주소 (dashboard/대시보드.html을 띄운 곳). 병원 관계자 로그인 뒤 이 주소로 보냄
  readonly VITE_DASHBOARD_URL?: string;
}
