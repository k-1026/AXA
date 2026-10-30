import { useEffect, useState } from 'react';
import type { HospitalData } from './types';

type State =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; data: HospitalData };

// 백엔드(backend/src/modules/hospital)가 생기기 전까지는 정적 JSON을 읽는다
export function useHospitals(): State {
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;
    fetch('/data/hospitals.json')
      .then((res) => {
        if (!res.ok) throw new Error(String(res.status));
        return res.json() as Promise<HospitalData>;
      })
      .then((data) => !cancelled && setState({ status: 'ready', data }))
      .catch(() => !cancelled && setState({ status: 'error' }));
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
