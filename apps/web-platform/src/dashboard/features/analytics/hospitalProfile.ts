// 로그인한 병원 정보: GET /tenant/me(이름·hospital_id) + /data/hospitals.json(구·진료시간·점심·가상 여부)
// 헤더 병원 이름, 대기 시간(진료시간 기준) 계산이 같이 씀. 한 번만 불러와 재사용 (로그아웃·다른 계정 로그인 시 resetHospitalProfile)
import { call } from './bookingShared';

export type HospitalProfile = {
  name: string;
  district: string | null;
  demo: boolean;
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
      const h = (d.items ?? []).find((x: { id: string | number }) => x.id === `DEMO-${me.hospital_id}` || String(x.id) === String(me.hospital_id));
      const m = /(\d{2}:\d{2})~(\d{2}:\d{2})/.exec(h?.lunchWeek || '');
      return {
        name: me.display_name || h?.name || '우리 병원',
        district: h?.district ?? null,
        demo: !!h?.demo,
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
