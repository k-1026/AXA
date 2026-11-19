// public/data/dashboard-public.json 구조 (data/etl/build_dashboard_public.py 가 만든다)
export type NameN = { name: string; n: number };
export type DeptKey = 'dermatology' | 'internal' | 'ophthalmology';

export type HoursStats = { total: number; known: number; night: number; saturday: number; sunday: number };
export type PriceStat = { item: string; unit: string; count: number; min: number; median: number; max: number; month: string };

export type PublicData = {
  patients: {
    byYear: { year: number; n: number }[];
    nationality2025: NameN[];
    departments2025: NameN[];
    summary2025: { real: number; female: number; male: number };
    growth: { name: string; national: number; growth: number; daegu: number; share: number }[];
    source: string;
  };
  residents: { nationality: NameN[]; byGu: NameN[]; total: number; source: string };
  visitors: { monthly: { month: string; n: number; days: number }[]; byGu2025: NameN[]; source: string; range: [string, string] };
  hours: { byDept: Record<DeptKey, HoursStats>; source: string };
  prices: { byDept: Partial<Record<DeptKey, PriceStat[]>>; source: string };
  registered: { total: number; byType: NameN[]; source: string };
  favorite: { hospitals: { hospital: string; procedures: string[] }[]; source: string };
};

export type Mode = 'initial' | 'operating';

export const DEPT_LABEL: Record<DeptKey, string> = {
  dermatology: '피부과',
  internal: '내과',
  ophthalmology: '안과',
};
