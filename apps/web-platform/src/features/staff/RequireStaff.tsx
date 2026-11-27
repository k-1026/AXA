import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { isStaffPreview, readStaffToken } from './staffSession';

// /dashboard는 직원 토큰이 있을 때만 (로컬 개발 미리보기 ?preview=1 은 예외 — staffSession.ts). 없으면 로그인 화면의 "병원 관계자" 쪽으로 보냄
export function RequireStaff({ children }: { children: ReactNode }) {
  if (!readStaffToken() && !isStaffPreview()) return <Navigate to="/login" replace state={{ from: '/dashboard', who: 'staff' }} />;
  return <>{children}</>;
}
