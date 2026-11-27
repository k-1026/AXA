import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { clearStaffToken } from '../../../features/staff/staffSession';

// 병원 API가 401(로그인 만료)을 주면: 직원 토큰을 지우고 로그인 화면의 "병원 관계자"로
export function useStaffExpired() {
  const navigate = useNavigate();
  return useCallback(() => {
    clearStaffToken();
    navigate('/login', { replace: true, state: { who: 'staff' } });
  }, [navigate]);
}
