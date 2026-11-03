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

export interface MyPageData {
  user: { name: string };
  stats: { saved: number; visits: number; recent: number };
  trip: { start: string; end: string };
  schedule: ScheduleItem[];
  checklist: ChecklistItem[];
}

export const SAMPLE_MYPAGE: MyPageData = {
  user: { name: 'Emma' },
  stats: { saved: 3, visits: 2, recent: 8 },
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
