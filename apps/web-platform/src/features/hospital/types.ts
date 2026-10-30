export type DepartmentKey = 'dermatology' | 'plastic' | 'internal' | 'dental';

export interface Hospital {
  id: string;
  name: string;
  type: string;
  district: string;
  addr: string;
  tel: string;
  lat: number;
  lng: number;
  depts: DepartmentKey[];
}

export interface HospitalData {
  meta: { source: string; fetchedAt: string };
  items: Hospital[];
}
