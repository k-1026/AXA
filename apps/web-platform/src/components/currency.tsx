import { createContext, useContext, useState, type ReactNode } from 'react';
import { readSetting, writeSetting } from './storage';

// 가격은 원화(KRW)로 저장. 가격 가이드에서 고른 통화로 참고용 환산 (환율: components/exchangeRates.ts)
export const CURRENCIES = ['KRW', 'USD', 'CNY', 'TWD', 'VND'] as const;
export type Currency = (typeof CURRENCIES)[number];

const CurrencyContext = createContext<{
  currency: Currency;
  setCurrency: (c: Currency) => void;
}>({ currency: 'KRW', setCurrency: () => {} });

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const saved = readSetting('currency') as Currency | null;
  const [currency, setState] = useState<Currency>(
    saved && CURRENCIES.includes(saved) ? saved : 'KRW',
  );
  const setCurrency = (c: Currency) => {
    setState(c);
    writeSetting('currency', c);
  };
  return (
    <CurrencyContext.Provider value={{ currency, setCurrency }}>
      {children}
    </CurrencyContext.Provider>
  );
}

export const useCurrency = () => useContext(CurrencyContext);
