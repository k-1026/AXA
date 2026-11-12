import { useTranslation } from 'react-i18next';
import { useAuth } from '../../components/auth';
import { useSavedHospitals } from '../hospital/savedHospitals';
import { useVisitLog } from './visitLog';
import { useHospitals } from '../hospital/useHospitals';
import { SAMPLE_MYPAGE, type MyPageData, type SavedHospital } from './sampleData';
import { hospitalNames } from '../hospital/name';

// 데모 계정은 예시 데이터, 실제 회원은 (백엔드 연결 전까지) 빈 상태에서 시작
const EMPTY: MyPageData = {
  user: { name: '' },
  stats: { saved: 0, visits: 0 },
  trip: { start: '', end: '' },
  schedule: [],
  checklist: SAMPLE_MYPAGE.checklist.map((c) => ({ ...c, done: false })),
};

export function useMyPageData(): { data: MyPageData; saved: SavedHospital[]; demo: boolean } {
  const { user } = useAuth();
  const { t } = useTranslation();
  const { saved: entries } = useSavedHospitals();
  const hospitals = useHospitals();
  const { visits } = useVisitLog();

  // 병원 정보 페이지에서 찜한 병원. 데이터에서 빠진 병원(폐업 등)은 보여주지 않는다
  const items = hospitals.status === 'ready' ? hospitals.data.items : [];
  const mine = entries.flatMap((e): SavedHospital[] => {
    const h = items.find((x) => x.id === e.id);
    if (!h) return [];
    const area = t(`district.${h.district}`);
    return [
      {
        id: h.id,
        savedAt: e.savedAt,
        dept: h.depts[0],
        name: hospitalNames(h),
        area: { ko: area, en: area },
        treatments: [],
        languages: [],
        prices: [],
        detailTo: `/hospitals/${encodeURIComponent(h.id)}`,
      },
    ];
  });

  if (user?.demo) {
    return { data: { ...SAMPLE_MYPAGE, stats: { ...SAMPLE_MYPAGE.stats, saved: mine.length, visits: visits.length } }, saved: mine, demo: true };
  }
  return {
    data: { ...EMPTY, user: { name: user?.name ?? '' }, stats: { ...EMPTY.stats, saved: mine.length, visits: visits.length } },
    saved: mine,
    demo: false,
  };
}
