// 병원 상세 페이지 조회 기록 (11/27) → 병원 대시보드 "상세페이지 방문자"
// - 방문자 값: 이 브라우저의 무작위 값, 한국 날짜가 바뀌면 새로 만듦 (개인정보 없음, 로그인과 무관)
// - 같은 날 같은 병원은 한 번만 보냄 (서버도 하루 한 번만 셈). 병원 직원으로 로그인한 탭은 보내지 않음
// - 실패해도 화면에는 영향 없음
import { API_BASE } from '../../components/api';
import { readSetting, writeSetting } from '../../components/storage';
import { todayKst } from '../../lib/common';
import { readStaffToken } from '../staff/staffSession';

const KEY = 'visitorKey';
const sent = new Set<string>();

function visitorKey(day: string): string {
  try {
    const saved = JSON.parse(readSetting(KEY) ?? 'null') as { day: string; key: string } | null;
    if (saved?.day === day && saved.key) return saved.key;
  } catch {
    /* 새로 만듦 */
  }
  const key = Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) => b.toString(16).padStart(2, '0')).join('');
  writeSetting(KEY, JSON.stringify({ day, key }));
  return key;
}

export function recordPageView(hospital: string, lang: string): void {
  if (readStaffToken()) return;
  const day = todayKst();
  if (sent.has(`${day}|${hospital}`)) return;
  sent.add(`${day}|${hospital}`);
  fetch(`${API_BASE}/hospitals/page-views`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hospital, visitor_key: visitorKey(day), lang }),
    keepalive: true,
  }).catch(() => {});
}
