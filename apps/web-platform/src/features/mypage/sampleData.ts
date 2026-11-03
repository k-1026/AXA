// 마이페이지 예시 데이터. 로그인·백엔드 연결 전까지 화면 확인용으로만 쓴다
// 병원 방문 일정은 사용자가 직접 등록한 것만 보여준다 (병원 추천 X, docs/compliance.md)

export interface Localized {
  ko: string;
  en: string;
}

export type ScheduleKind = 'hospital' | 'experience' | 'tour';

export interface ScheduleItem {
  id: string;
  date: string; // YYYY-MM-DD (한국 시간)
  time: string; // HH:mm
  kind: ScheduleKind;
  title: Localized;
  place: Localized[]; // " · "로 이어 붙여 표시
  addedBy: 'user';
  mapQuery?: string; // 길찾기 링크용 검색어
}

export interface ChecklistItem {
  key: string; // i18n: mypage.checklist.items.<key>
  done: boolean;
}

// 저장한 병원. 진료과는 마이페이지 필터용 (치과는 병원 데이터 진료과에 아직 없음)
export type SavedDept = 'dermatology' | 'dental' | 'plastic' | 'internal' | 'ophthalmology';

export const SAVED_DEPTS: { key: SavedDept; label: Localized }[] = [
  { key: 'dermatology', label: { ko: '피부과', en: 'Dermatology' } },
  { key: 'dental', label: { ko: '치과', en: 'Dentistry' } },
  { key: 'plastic', label: { ko: '성형외과', en: 'Plastic Surgery' } },
  { key: 'internal', label: { ko: '내과', en: 'Internal Medicine' } },
  { key: 'ophthalmology', label: { ko: '안과', en: 'Ophthalmology' } },
];

export interface SavedHospital {
  id: string;
  savedAt: string; // YYYY-MM-DD, "최근 저장순" 정렬용
  dept: SavedDept;
  name: Localized;
  area: Localized;
  treatments: Localized[];
  languages: Localized[];
  // 가격은 출처 있는 숫자만 넣는다. 없으면 "가격 확인 중"
  prices: { name: Localized; range?: string }[];
  detailTo: string;
  real?: boolean; // 병원 정보 페이지에서 직접 찜한 실제 병원 (없으면 예시)
}

export interface MyPageData {
  user: { name: string };
  stats: { saved: number; visits: number; recent: number };
  trip: { start: string; end: string };
  schedule: ScheduleItem[];
  checklist: ChecklistItem[];
}

export const SAMPLE_MYPAGE: MyPageData = {
  user: { name: 'Emma' },
  stats: { saved: 2, visits: 2, recent: 8 },
  trip: { start: '2026-11-20', end: '2026-11-22' },
  schedule: [
    {
      id: 's1',
      date: '2026-11-20',
      time: '10:00',
      kind: 'hospital',
      title: { ko: '병원 방문', en: 'Hospital visit' },
      place: [{ ko: '중구', en: 'Jung-gu' }],
      addedBy: 'user',
      mapQuery: '대구 중구',
    },
    {
      id: 's2',
      date: '2026-11-20',
      time: '14:00',
      kind: 'experience',
      title: { ko: '약령시 둘러보기', en: 'Yangnyeongsi herbal market' },
      place: [{ ko: '대구 중구', en: 'Jung-gu, Daegu' }],
      addedBy: 'user',
    },
    {
      id: 's3',
      date: '2026-11-21',
      time: '11:00',
      kind: 'tour',
      title: { ko: '대구 시티 투어', en: 'Daegu city tour' },
      place: [
        { ko: '83타워', en: '83 Tower' },
        { ko: '두류공원', en: 'Duryu Park' },
      ],
      addedBy: 'user',
    },
  ],
  checklist: [
    { key: 'saveAddress', done: true },
    { key: 'setLanguage', done: true },
    { key: 'checkHours', done: false },
    { key: 'checkInterpreter', done: false },
    { key: 'checkNotice', done: false },
  ],
};

// 병원명·이미지·가격은 화면 구성을 위한 예시. 실제 병원이 아님
export const SAMPLE_SAVED_HOSPITALS: SavedHospital[] = [
  {
    id: 'h1',
    savedAt: '2026-11-02',
    dept: 'dermatology',
    name: { ko: '메디 피부과의원', en: 'Medi Dermatology Clinic' },
    area: { ko: '대구 중구 · 동성로', en: 'Dongseong-ro, Jung-gu' },
    treatments: [
      { ko: '피부관리', en: 'Skin care' },
      { ko: '레이저', en: 'Laser' },
      { ko: '색소관리', en: 'Pigmentation' },
    ],
    languages: [
      { ko: '한국어', en: 'Korean' },
      { ko: '영어', en: 'English' },
    ],
    prices: [
      { name: { ko: '기미·잡티 레이저', en: 'Spot laser' } },
      { name: { ko: '여드름 진료', en: 'Acne care' } },
    ],
    detailTo: '/prices?dept=dermatology',
  },
  {
    id: 'h2',
    savedAt: '2026-10-28',
    dept: 'dental',
    name: { ko: '메디 치과의원', en: 'Medi Dental Clinic' },
    area: { ko: '대구 수성구 · 범어동', en: 'Beomeo-dong, Suseong-gu' },
    treatments: [
      { ko: '스케일링', en: 'Scaling' },
      { ko: '치아미백', en: 'Whitening' },
      { ko: '구강검진', en: 'Oral exam' },
    ],
    languages: [
      { ko: '한국어', en: 'Korean' },
      { ko: '영어', en: 'English' },
    ],
    prices: [
      { name: { ko: '스케일링', en: 'Scaling' } },
      { name: { ko: '치아미백', en: 'Whitening' } },
    ],
    detailTo: '/prices',
  },
];
