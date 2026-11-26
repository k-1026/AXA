// 로그인한 병원 정보: GET /tenant/me(이름·hospital_id) + /data/hospitals.json(구·진료시간·점심·가상 여부)
// 헤더 병원 이름·진료과, 대기 시간(진료시간 기준) 계산이 같이 씀. 토큰별로 한 번만 불러와 재사용 (다른 계정으로 로그인하면 토큰이 바뀌어 새로 불러옴)
import { call } from './bookingShared';
import { applyOverride } from '../../../features/hospital/overrides';
import type { Hospital } from '../../../features/hospital/types';

export type HospitalProfile = {
  hospital: Hospital | null; // 병원 목록의 이 병원 (병원이 고친 값 반영) — 마이 병원 화면이 씀
  name: string;
  district: string | null;
  demo: boolean;
  depts: string[]; // 진료과 코드 (dermatology·plastic·ophthalmology …)
  hours: ([string, string] | null)[] | null; // 월~일
  lunch: [string, string] | null;
};

let cached: { token: string; p: Promise<HospitalProfile | null> } | null = null;

export function loadHospitalProfile(token: string | null): Promise<HospitalProfile | null> {
  if (!token) return Promise.resolve(null);
  if (cached?.token === token) return cached.p;
  const p = (async (): Promise<HospitalProfile | null> => {
    try {
      const me = await call<{ hospital_id: number; display_name: string }>('/tenant/me');
      const d = await fetch('/data/hospitals.json').then((r) => r.json()).catch(() => ({}));
      const raw = (d.items ?? []).find((x: { id: string | number }) => x.id === `DEMO-${me.hospital_id}` || String(x.id) === String(me.hospital_id));
      const h: Hospital | undefined = raw ? applyOverride(raw) : undefined; // 마이 병원에서 고친 진료시간 등 반영
      const m = /(\d{2}:\d{2})~(\d{2}:\d{2})/.exec(h?.lunchWeek || '');
      return {
        hospital: h ?? null,
        name: me.display_name || h?.name || '우리 병원',
        district: h?.district ?? null,
        demo: !!h?.demo,
        depts: Array.isArray(h?.depts) ? h.depts : [],
        hours: Array.isArray(h?.hours) ? h.hours : null,
        lunch: m ? [m[1], m[2]] as [string, string] : null,
      };
    } catch {
      cached = null; // 실패하면 다음에 다시 시도
      return null;
    }
  })();
  cached = { token, p };
  return p;
}

// 마이 병원에서 저장한 뒤: 다음에 부를 때 새로 읽게 (헤더·대기 시간 계산도 새 진료시간으로)
export function refreshHospitalProfile() {
  cached = null;
}
