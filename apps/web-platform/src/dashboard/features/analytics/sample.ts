// 프로토타입용 가상 병원과 운영 예시 데이터. 실제 병원·실제 환자 데이터가 아님 → 화면에 "예시" 배지
import type { DeptKey } from './types';

export const SAMPLE_DISTRICT = '수성구';

// 우리 병원 진료시간 (예시) — 대구 같은 진료과와 비교할 때 씀
export const SAMPLE_HOURS = { night: true, saturday: true, sunday: false };

// 병원 정보 등록 상태 (초기 화면 설정 항목)
export type SetupItem = { key: string; label: string; hint: string; done: boolean; from?: string };
export const SETUP_ITEMS: SetupItem[] = [
  { key: 'hours', label: '진료시간', hint: '심평원 신고 시간을 불러왔어요. 점심·접수 마감만 확인해 주세요', done: true, from: '심평원' },
  { key: 'homepage', label: '홈페이지·SNS', hint: '홈페이지 1개, 인스타그램 1개 연결됨', done: true, from: '팀 수집' },
  { key: 'registration', label: '유치의료기관 등록번호', hint: '등록번호를 확인하면 환자 화면에 "등록 유치의료기관"이 표시돼요', done: false },
  { key: 'languages', label: '통역 가능 언어', hint: '병원에서 직접 응대 가능한 언어와 통역 연결 방법', done: false },
  { key: 'consultHours', label: '상담 가능 시간', hint: '이 시간 기준으로 첫 답변 시간을 계산해요', done: true },
  { key: 'slots', label: '예약 가능 일정', hint: '요일·시간대별로 받을 수 있는 예약 수', done: false },
  { key: 'price', label: '가격 안내', hint: '진료항목별 가격 범위 또는 "견적 요청" 안내', done: false },
];

// ── 운영 후 예시 ──
export const KPI = [
  { label: '상세페이지 방문자', now: 1240, prev: 1051, unit: '명' },
  { label: '상담 신청', now: 86, prev: 79, unit: '건' },
  { label: '예약 확정', now: 31, prev: 33, unit: '건' },
  { label: '방문 완료', now: 24, prev: 23, unit: '건' },
  { label: '취소율', now: 12, prev: 9, unit: '%', lowerIsBetter: true },
];

export const TODAY = { newConsults: 5, bookingRequests: 3, visitsToday: 2, unanswered: 4 };

export const CHANNELS = [
  { name: '메디대구 지도·목록', visits: 610, consults: 41, bookings: 16 },
  { name: '인스타그램 링크', visits: 380, consults: 29, bookings: 5 },
  { name: '블로그 링크', visits: 150, consults: 9, bookings: 6 },
  { name: '유치업체 A 링크', visits: 100, consults: 7, bookings: 4 },
];

export const LANGUAGES = [
  { name: '중국어(번체)', consults: 31, bookings: 13 },
  { name: '영어', consults: 22, bookings: 9 },
  { name: '중국어(간체)', consults: 18, bookings: 6 },
  { name: '베트남어', consults: 12, bookings: 1 },
  { name: '한국어', consults: 3, bookings: 2 },
];

export const TREATMENTS: Record<DeptKey, { name: string; views: number; consults: number }[]> = {
  dermatology: [
    { name: '피코 토닝', views: 420, consults: 26 },
    { name: '리프팅 (HIFU)', views: 360, consults: 9 },
    { name: '보톡스', views: 240, consults: 21 },
    { name: '여드름 흉터', views: 150, consults: 12 },
  ],
  internal: [
    { name: '건강검진', views: 380, consults: 28 },
    { name: '위·대장 내시경', views: 300, consults: 8 },
    { name: '예방접종', views: 170, consults: 15 },
    { name: '초음파 검사', views: 140, consults: 11 },
  ],
  ophthalmology: [
    { name: '라식·라섹', views: 450, consults: 25 },
    { name: '스마일 라식', views: 330, consults: 7 },
    { name: '백내장 (다초점)', views: 190, consults: 14 },
    { name: '드림렌즈', views: 90, consults: 6 },
  ],
};

export const BUTTONS = [
  { name: '상담하기', n: 214 },
  { name: '길찾기', n: 168 },
  { name: '전화', n: 95 },
  { name: '찜', n: 88 },
  { name: '홈페이지', n: 61 },
];

export const PRE_VISIT_QUESTIONS = [
  { name: '통역이 되나요?', n: 19, fix: '상세페이지에 응대 언어 표시' },
  { name: '카드·위챗페이 결제', n: 14, fix: '결제 수단 안내 추가' },
  { name: '위치·주차', n: 11, fix: '지하철역 기준 길 안내' },
  { name: '예상 비용', n: 10, fix: '항목별 가격 범위 등록' },
];

export const FUNNEL = [
  { name: '병원 상세 조회', n: 1240 },
  { name: '상담 시작', n: 86 },
  { name: '예약 신청', n: 48 },
  { name: '예약 확정', n: 31 },
  { name: '방문 완료', n: 24 },
];

export const FIRST_REPLY = { medianMin: 160, prevMedianMin: 210, within1h: 38, outsideHours: 27 };

export const CANCEL_REASONS = [
  { name: '일정 변경', n: 6 },
  { name: '비용', n: 3 },
  { name: '통역', n: 2 },
  { name: '다른 병원 선택', n: 2 },
  { name: '교통', n: 1 },
  { name: '기타·미응답', n: 3 },
];

export const REPEAT_CHANGES = 3;

// 희망 요일별 신청 수와 확정 수
export const PREFERRED_DAYS = [
  { name: '월', req: 5, ok: 4 },
  { name: '화', req: 4, ok: 3 },
  { name: '수', req: 6, ok: 5 },
  { name: '목', req: 5, ok: 4 },
  { name: '금', req: 9, ok: 6 },
  { name: '토', req: 17, ok: 8 },
  { name: '일', req: 2, ok: 1 },
];

export const AFTERCARE_STATUS = [
  { name: '신규 문의', n: 6 },
  { name: '미답변', n: 2 },
  { name: '처리 중', n: 3 },
  { name: '해결 완료', n: 18 },
];

export const AFTERCARE_KEYWORDS = [
  { name: '안내 부족', now: 7, prev: 4 },
  { name: '재방문 일정', now: 6, prev: 6 },
  { name: '통역', now: 4, prev: 5 },
  { name: '비용 설명', now: 3, prev: 1 },
  { name: '대기시간', now: 2, prev: 3 },
];

export const AFTERCARE_CASE = {
  who: '대만 · 30대 · 방문 11/03',
  summary: '귀국 후 관리 방법 안내문을 못 받았다고 문의. 중국어(번체) 안내문을 다시 보내고 해결.',
  keyword: '안내 부족',
};

export const IMPROVEMENTS = [
  { date: '10/20', change: '방문 후 안내문에 중국어(번체) 추가', before: 5, after: 2, keyword: '안내 부족' },
  { date: '10/02', change: '상세페이지에 주차·지하철 안내 추가', before: 9, after: 4, keyword: '위치' },
];

export const SATISFACTION = { score: 4.6, responses: 17 };
