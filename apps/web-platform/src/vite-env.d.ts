/// <reference types="vite/client" />

interface ImportMetaEnv {
  // 백엔드 주소. 없으면 로컬 개발 서버 (http://localhost:8000)
  readonly VITE_API_URL?: string;
  readonly VITE_SUPABASE_PUBLISHABLE_KEY?: string; // 실시간 알림 (공개 키만)
  readonly VITE_SHOW_CHAT_TIMING?: string; // "true"면 배포 빌드에서도 챗봇 답 옆에 걸린 시간 표시 (테스트용)
}
