export type DepartmentKey = 'dermatology' | 'plastic' | 'internal' | 'dental';

// 빈 값은 데이터에서 빠져 있음 (undefined) → 화면에서 빈칸
export interface Hospital {
  id: string;
  name: string;
  type: string;
  district: string;
  addr: string;
  tel?: string;
  url?: string;
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
}

export interface HospitalData {
  meta: { source: string; fetchedAt: string };
  items: Hospital[];
}
