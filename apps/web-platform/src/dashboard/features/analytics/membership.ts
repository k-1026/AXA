// 병원 회원 등급 (요금안 v4: 기본 회원 무료 + 수수료 13% / 프리미엄 연 ₩1,800,000 + 수수료 8%, 금액은 가정값)
// "마이 병원"에서 바꾸고, "진료·결제 확인" 등 다른 탭이 같은 값을 씀
// 백엔드에 등급 저장 API가 없어 지금은 이 브라우저(localStorage)에만 저장 — 생기면 read·save만 API로 교체
import { useEffect, useState } from 'react';

export type Tier = 'basic' | 'premium';
export const TIERS: Record<Tier, { name: string; rate: number; yearFee: number; desc: string }> = {
  basic: { name: '기본 회원', rate: 0.13, yearFee: 0, desc: '회원비 없음 · 방문 완료·결제 확인된 진료비의 13%' },
  premium: { name: '프리미엄 회원', rate: 0.08, yearFee: 1800000, desc: '연 ₩1,800,000 (월 ₩150,000) · 방문 완료·결제 확인된 진료비의 8%' },
};

const KEY = 'md.dashboard.membership';
const EVENT = 'md-membership';

function read(): Tier {
  try { return localStorage.getItem(KEY) === 'basic' ? 'basic' : 'premium'; } catch { return 'premium'; }
}

export function saveTier(t: Tier) {
  try { localStorage.setItem(KEY, t); } catch { /* 무시 */ }
  window.dispatchEvent(new Event(EVENT)); // 같은 화면의 다른 탭 컴포넌트도 바로 반영
}

export function useTier(): Tier {
  const [tier, setTier] = useState<Tier>(read);
  useEffect(() => {
    const on = () => setTier(read());
    window.addEventListener(EVENT, on);
    window.addEventListener('storage', on);
    return () => { window.removeEventListener(EVENT, on); window.removeEventListener('storage', on); };
  }, []);
  return tier;
}
