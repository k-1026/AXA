import { useAuth } from '../../components/auth';
import { SAMPLE_MYPAGE, SAMPLE_SAVED_HOSPITALS, type MyPageData, type SavedHospital } from './sampleData';

// 데모 계정은 예시 데이터, 실제 회원은 (백엔드 연결 전까지) 빈 상태에서 시작
const EMPTY: MyPageData = {
  user: { name: '' },
  stats: { saved: 0, visits: 0, recent: 0 },
  trip: { start: '', end: '' },
  schedule: [],
  checklist: SAMPLE_MYPAGE.checklist.map((c) => ({ ...c, done: false })),
};

export function useMyPageData(): { data: MyPageData; saved: SavedHospital[]; demo: boolean } {
  const { user } = useAuth();
  if (user?.demo) return { data: SAMPLE_MYPAGE, saved: SAMPLE_SAVED_HOSPITALS, demo: true };
  return { data: { ...EMPTY, user: { name: user?.name ?? '' } }, saved: [], demo: false };
}
