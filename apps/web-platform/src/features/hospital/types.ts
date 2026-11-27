export type DepartmentKey = 'dermatology' | 'plastic' | 'internal' | 'ophthalmology' | 'korean_medicine' | 'other'; // other: 치과·한방·종합병원 등 등록 유치기관

// 빈 값은 데이터에서 빠져 있음 (undefined) → 화면에서 빈칸
export interface Hospital {
  id: string;
  /** 시연용 가상 병원 (data/processed/demo/demo_hospital.json). 이름 뒤에 "시연용" 표시, 예시 일정·예약은 이 병원만 */
  demo?: true;
  name: string;
  nameEn: string; // 한국어 외 모든 언어에서 쓰는 영어 이름
  type: string;
  district: string;
  addr: string;
  tel?: string;
  url?: string;
  instagram?: string;
  photo?: string;
  lat: number;
  lng: number;
  depts: DepartmentKey[];
  /** 월~일 [시작, 끝], 정보 없는 요일은 null */
  hours?: ([string, string] | null)[];
  lunchWeek?: string;
  lunchSat?: string;
  rcvWeek?: string;
  rcvSat?: string;
  /** 'closed' 또는 원문 메모 */
  sunday?: string;
  holiday?: string;
  emergencyDay?: boolean;
  emergencyNight?: boolean;
  parking?: number;
  parkingFee?: boolean;
  /** 아래는 병원이 대시보드 "마이 병원"에서 직접 넣는 칸 (features/hospital/overrides.ts) */
  email?: string;
  /** 진료·상담 가능 언어 코드 (ko·en·zh-CN·zh-TW·ja·vi·ru·mn·th) */
  languages?: string[];
  parkingNote?: string;
  /** 병원이 직접 고친 정보가 있음 → 상세 페이지에 "병원이 직접 수정" 표시 */
  edited?: true;
}

export interface HospitalData {
  meta: { source: string; fetchedAt: string };
  items: Hospital[];
}
