import { useEffect, useState } from 'react';
import type { HospitalData } from './types';

type State =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; data: HospitalData };

// 메뉴를 옮겨 다녀도 한 번만 받도록 캐시
let cache: Promise<HospitalData> | null = null;

function load(): Promise<HospitalData> {
  cache ??= fetch('/data/hospitals.json').then((res) => {
    if (!res.ok) throw new Error(String(res.status));
    return res.json() as Promise<HospitalData>;
  });
  cache.catch(() => {
    cache = null;
  });
  return cache;
}

// 백엔드(backend/src/modules/hospital)가 생기기 전까지는 정적 JSON을 읽는다
export function useHospitals(): State {
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;
    load()
      .then((data) => !cancelled && setState({ status: 'ready', data }))
      .catch(() => !cancelled && setState({ status: 'error' }));
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
