import { useEffect, useState } from 'react';
import { api } from './api';
import type { Currency } from './currency';

// 환율은 백엔드가 매일 오전 10시(한국 시간)에 정하는 그날 적용 값 (GET /exchange-rates, 한국은행 ECOS)
// 가격은 원화로 저장되어 있고, 고른 통화로는 참고용 환산만 한다
export interface ExchangeRates {
  base: 'KRW';
  rates: Partial<Record<Currency, number>>; // 1원 = rate
  applied_on: string; // 이 환율로 안내하는 날 (YYYY-MM-DD)
  base_date: string; // 한국은행 통계 기준일 (영업일)
  switch_hour_kst: number;
  stale: boolean;
  provider: { name: string; url: string };
}

type State = { status: 'loading' } | { status: 'ready'; data: ExchangeRates } | { status: 'error' };

let cache: Promise<ExchangeRates> | null = null; // 화면을 옮겨 다녀도 한 번만 요청

export function useExchangeRates(enabled: boolean): State {
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    cache ??= api<ExchangeRates>('/exchange-rates').catch((e) => {
      cache = null; // 실패하면 다음에 다시 시도
      throw e;
    });
    cache
      .then((data) => alive && setState({ status: 'ready', data }))
      .catch(() => alive && setState({ status: 'error' }));
    return () => {
      alive = false;
    };
  }, [enabled]);

  return state;
}

// 원화 금액 → 고른 통화 (소수점 없이 반올림). 통화 기호·자리 구분은 화면 언어 형식으로
export function formatConverted(krw: number, currency: Currency, rate: number, lang: string): string {
  return new Intl.NumberFormat(lang, {
    style: 'currency',
    currency,
    currencyDisplay: 'symbol', // narrowSymbol은 TWD도 '$'라 USD와 헷갈림 → NT$·CN¥처럼
    maximumFractionDigits: 0,
  }).format(krw * rate);
}
