import { useEffect } from 'react';
import { useAuth } from '../../components/auth';
import { readSetting, writeSetting } from '../../components/storage';
import { useHospitals } from '../hospital/useHospitals';
import { seedSavedIfEmpty } from '../hospital/savedHospitals';
import { seedVisitsIfEmpty } from './visitLog';

// 시연 환자 계정(backend/scripts/seed_demo_shared.py가 만듦)으로 처음 로그인하면 찜·방문 기록 예시를 이 브라우저에 넣는다.
// 찜·방문 기록은 아직 서버가 아니라 계정별 브라우저 저장이라 DB 시드로는 못 넣음 → 서버 저장으로 바뀌면 이 파일은 지우고 시드로 옮기기
// - 한 브라우저에서 한 번만 (지운 뒤 다시 채우지 않음). 다른 계정에는 아무것도 안 함
// - 방문 기록은 가상 병원 9001과 직접 입력한 예시 이름만 (실제 병원에 가짜 방문 기록을 붙이지 않음)
// - 찜은 가상 병원 + 실제 등록 병원 2곳 (찜은 사용자가 고른 표시일 뿐, 병원에 대한 지어낸 정보 없음)
const DEMO_PATIENT_EMAIL = 'demo-patient@example.com';
const DEMO_HOSPITAL_ID = 'DEMO-9001';

export function useDemoPatientSeed() {
  const { user, account } = useAuth();
  const hospitals = useHospitals();

  useEffect(() => {
    if (user?.demo || user?.email !== DEMO_PATIENT_EMAIL || hospitals.status !== 'ready') return;
    const flag = `demoSeeded@${account}`;
    if (readSetting(flag)) return;
    const items = hospitals.data.items;
    const pick = (dept: string) => items.find((h) => h.id !== DEMO_HOSPITAL_ID && h.depts[0] === dept)?.id;
    const saved = [DEMO_HOSPITAL_ID, pick('dermatology'), pick('plastic')].filter((id): id is string => !!id && items.some((h) => h.id === id));
    seedSavedIfEmpty(saved);
    seedVisitsIfEmpty([
      { hospitalName: '西門市場附近藥局（示範）', date: '2026-11-13', note: '買防曬乳和保濕霜（示範紀錄）' },
      { hospitalId: DEMO_HOSPITAL_ID, hospitalName: 'Example Dermatology Clinic', date: '2026-11-12', note: '雷射淨膚 1 次，醫生說 4 週後可以再做（示範紀錄）' },
    ]);
    writeSetting(flag, new Date().toISOString());
  }, [user, account, hospitals]);
}
