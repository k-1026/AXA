import { useEffect } from 'react';
import { useAuth } from '../../components/auth';
import { readSetting, writeSetting } from '../../components/storage';
import { useHospitals } from '../hospital/useHospitals';
import { seedSavedIfEmpty } from '../hospital/savedHospitals';
import { seedPlansIfEmpty } from './tripSchedule';

// 시연 환자 계정(backend/scripts/seed_demo_shared.py가 만듦)으로 처음 로그인하면 찜·여행 일정 예시를 이 브라우저에 넣는다.
// 찜·방문 기록은 아직 서버가 아니라 계정별 브라우저 저장이라 DB 시드로는 못 넣음 → 서버 저장으로 바뀌면 이 파일은 지우고 시드로 옮기기
// - 한 브라우저에서 한 번만 (지운 뒤 다시 채우지 않음). 다른 계정에는 아무것도 안 함
// - 찜은 가상 병원 + 실제 등록 병원 2곳 (찜은 사용자가 고른 표시일 뿐, 병원에 대한 지어낸 정보 없음)
const DEMO_PATIENT_EMAIL = 'demo-patient@example.com';
const DEMO_HOSPITAL_ID = 'DEMO-9001';

export function useDemoPatientSeed() {
  const { user, account } = useAuth();
  const hospitals = useHospitals();

  useEffect(() => {
    if (user?.demo || user?.email !== DEMO_PATIENT_EMAIL || hospitals.status !== 'ready') return;
    const flag = `demoSeeded.v2@${account}`; // v2: 여행 일정 예시 추가 (비어 있는 목록만 채우므로 다시 돌아도 중복 없음)
    if (readSetting(flag)) return;
    const items = hospitals.data.items;
    const pick = (dept: string) => items.find((h) => h.id !== DEMO_HOSPITAL_ID && h.depts[0] === dept)?.id;
    const saved = [DEMO_HOSPITAL_ID, pick('dermatology'), pick('plastic')].filter((id): id is string => !!id && items.some((h) => h.id === id));
    seedSavedIfEmpty(saved);
    // 방문 기록은 방문 완료된 예약에서 자동으로 뜸 (2026-11-26) → 따로 넣지 않음
    seedPlansIfEmpty([
      { date: '2026-11-22', time: '10:00', text: '藥令市韓方街逛逛（示範）' },
      { date: '2026-11-23', time: '18:30', text: '西門市場夜市吃扁餃子（示範）' },
      { date: '2026-11-24', text: '買伴手禮、整理行李（示範）' },
    ]);
    writeSetting(flag, new Date().toISOString());
  }, [user, account, hospitals]);
}
