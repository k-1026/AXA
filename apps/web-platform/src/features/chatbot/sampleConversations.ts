// 챗봇 대화 기록 예시 데이터. 데모 계정에서만 보여주고 화면에 "예시"로 표시한다
// 실제 상담 기록이 아님. 병원 이름은 넣지 않는다 (병원 추천 X, docs/compliance.md)
import type { Conversation } from './types';

const T = (ko: string, en: string) => ({ ko, en });
const GREETING = T(
  '안녕하세요! 대구 의료관광 도우미 메디입니다.\n병원 정보부터 대구 여행까지, 무엇이 궁금하신가요?',
  "Hello! I'm Medi, your Daegu medical travel helper.\nWhat would you like to know, from hospitals to travel in Daegu?",
);

export const SAMPLE_CONVERSATIONS: Conversation[] = [
  {
    id: 'sample-1103-pm',
    createdAt: '2026-11-03T16:20:00+09:00',
    topic: 'hospital',
    dept: 'dermatology',
    sample: true,
    messages: [
      { id: 'a1', role: 'bot', text: GREETING, at: '2026-11-03T16:20:00+09:00' },
      {
        id: 'a2',
        role: 'user',
        text: T('영어 상담이 가능한 피부과를 찾고 싶어요.', "I'm looking for a dermatology clinic with English consultation."),
        at: '2026-11-03T16:21:00+09:00',
      },
      {
        id: 'a3',
        role: 'bot',
        text: T(
          '어느 지역을 중심으로 찾아볼까요?\n지역을 선택하면 병원 정보와 공식 상담 채널을 안내해 드릴게요.',
          "Which area should we look in?\nPick an area and I'll show hospital information and official contact channels.",
        ),
        at: '2026-11-03T16:21:00+09:00',
        chips: [
          { label: T('중구 · 동성로', 'Jung-gu · Dongseong-ro'), action: { kind: 'region', district: '중구' } },
          { label: T('수성구', 'Suseong-gu'), action: { kind: 'region', district: '수성구' } },
          { label: T('지역 상관없어요', 'Any area'), action: { kind: 'region', district: null } },
        ],
      },
    ],
  },
  {
    id: 'sample-1103-am',
    createdAt: '2026-11-03T10:12:00+09:00',
    topic: 'tour',
    sample: true,
    messages: [
      { id: 'b1', role: 'bot', text: GREETING, at: '2026-11-03T10:12:00+09:00' },
      { id: 'b2', role: 'user', text: T('진료 끝나고 가볼 만한 곳이 있을까요?', 'Any places to visit after my appointment?'), at: '2026-11-03T10:13:00+09:00' },
      {
        id: 'b3',
        role: 'bot',
        text: T(
          '대구 관광 정보는 대구 공식 관광 사이트에서 확인할 수 있어요. 시술 직후에는 무리한 일정은 피하고, 회복 안내는 병원에 꼭 확인해 주세요.',
          'You can find Daegu travel information on the official Daegu tourism site. Avoid a heavy schedule right after treatment, and check recovery advice with your hospital.',
        ),
        at: '2026-11-03T10:13:00+09:00',
      },
    ],
  },
  {
    id: 'sample-1102',
    createdAt: '2026-11-02T15:05:00+09:00',
    topic: 'price',
    sample: true,
    messages: [
      { id: 'c1', role: 'bot', text: GREETING, at: '2026-11-02T15:05:00+09:00' },
      { id: 'c2', role: 'user', text: T('스케일링 비용이 궁금해요.', 'How much does scaling cost?'), at: '2026-11-02T15:06:00+09:00' },
      {
        id: 'c3',
        role: 'bot',
        text: T(
          '시술별 가격 범위는 가격 가이드에서 볼 수 있어요. 실제 비용은 병원마다 다르니 병원에 꼭 확인해 주세요.',
          'You can see price ranges by treatment in the Price Guide. Actual costs vary, so please confirm with the hospital.',
        ),
        at: '2026-11-02T15:06:00+09:00',
        chips: [{ label: T('가격 가이드 보기', 'Open Price Guide'), action: { kind: 'link', to: '/prices' } }],
      },
    ],
  },
  {
    id: 'sample-1031',
    createdAt: '2026-10-31T11:30:00+09:00',
    topic: 'hospital',
    sample: true,
    messages: [
      { id: 'd1', role: 'bot', text: GREETING, at: '2026-10-31T11:30:00+09:00' },
      { id: 'd2', role: 'user', text: T('안과는 어디서 찾을 수 있어요?', 'Where can I find eye clinics?'), at: '2026-10-31T11:31:00+09:00' },
      {
        id: 'd3',
        role: 'bot',
        text: T('병원 정보에서 안과 목록을 거리순·가나다순으로 볼 수 있어요.', 'You can see eye clinics in Hospital Info, sorted by distance or name.'),
        at: '2026-10-31T11:31:00+09:00',
        chips: [{ label: T('병원 정보에서 보기', 'View in Hospital Info'), action: { kind: 'link', to: '/hospitals?dept=ophthalmology' } }],
      },
    ],
  },
  {
    id: 'sample-1028',
    createdAt: '2026-10-28T14:15:00+09:00',
    topic: 'interpret',
    sample: true,
    messages: [
      { id: 'e1', role: 'bot', text: GREETING, at: '2026-10-28T14:15:00+09:00' },
      { id: 'e2', role: 'user', text: T('병원에서 통역을 받을 수 있나요?', 'Can I get an interpreter at the hospital?'), at: '2026-10-28T14:16:00+09:00' },
      {
        id: 'e3',
        role: 'bot',
        text: T(
          '통역 지원은 병원마다 달라요. 방문 전에 병원 공식 연락처로 지원 언어를 확인해 주세요. 관광 통역이 필요하면 1330 관광통역안내전화를 이용할 수 있어요.',
          'Interpreter support varies by hospital. Please check supported languages through the hospital’s official contact before visiting. For travel interpretation, you can call the 1330 Korea Travel Hotline.',
        ),
        at: '2026-10-28T14:16:00+09:00',
      },
    ],
  },
];

export { GREETING };
