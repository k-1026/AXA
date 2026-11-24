import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { readStaffToken } from './staffSession';

// /dashboard는 직원 토큰이 있을 때만. 없으면 로그인 화면의 "병원 관계자" 쪽으로 보냄
export function RequireStaff({ children }: { children: ReactNode }) {
  if (!readStaffToken()) return <Navigate to="/login" replace state={{ from: '/dashboard', who: 'staff' }} />;
  return <>{children}</>;
}
