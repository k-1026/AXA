import type { ConsultThread } from './types';

// 데모 계정용 예시 상담. 병원 이름·대화는 화면 구성을 위한 예시이고 실제 병원이 아니다
export const SAMPLE_THREADS: ConsultThread[] = [
  {
    hospitalId: 'sample-medibom',
    name: { ko: '메디봄 피부과', en: 'Medibom Dermatology' },
    dept: 'dermatology',
    district: '중구',
    unread: 2,
    sample: true,
    messages: [
      { id: 's1-0', from: 'user', at: '2026-10-28T11:00:00+09:00', booking: { date: '2026-11-03', time: '11:00', language: 'en', status: 'confirmed', bookingNo: 'MD-261028-004', treatment: { ko: '피코 토닝', en: 'Pico toning' } } },
      { id: 's1-1', from: 'staff', at: '2026-11-10T14:20:00+09:00', text: { ko: '안녕하세요. 메디봄 피부과 상담 담당자입니다.\n방문 전 궁금한 내용을 남겨 주세요.', en: 'Hello, this is the consultation desk at Medibom Dermatology.\nLeave any questions you have before your visit.' } },
      { id: 's1-2', from: 'user', at: '2026-11-10T14:22:00+09:00', text: { ko: '안녕하세요. 11월 14일에 방문하고 싶은데 영어 상담이 가능한가요?', en: "Hi, I'd like to visit on November 14. Is a consultation in English available?" } },
      { id: 's1-3', from: 'staff', at: '2026-11-10T14:23:00+09:00', text: { ko: '네, 영어 상담 가능합니다. 희망 시간을 선택해 예약을 신청해 주세요.', en: 'Yes, English consultations are available. Choose a time and send a booking request.' } },
      { id: 's1-4', from: 'user', at: '2026-11-10T14:25:00+09:00', booking: { date: '2026-11-14', time: '14:00', language: 'en', status: 'confirmed', bookingNo: 'MD-261110-001' } },
      { id: 's1-5', from: 'staff', at: '2026-11-10T14:40:00+09:00', text: { ko: '11월 14일 오후 2시로 예약이 확정되었습니다. 방문 시 여권을 지참해 주세요.', en: 'Your booking for November 14 at 2:00 PM is confirmed. Please bring your passport.' } },
    ],
  },
  {
    hospitalId: 'sample-daegumiso',
    name: { ko: '대구미소 내과', en: 'Daegu Miso Internal Medicine' },
    dept: 'internal',
    district: '수성구',
    unread: 0,
    sample: true,
    messages: [
      { id: 's2-1', from: 'user', at: '2026-11-08T10:05:00+09:00', text: { ko: '건강검진을 받고 싶은데 다음 주에 예약 가능한 날짜가 있을까요?', en: 'I would like a health checkup. Are there any available dates next week?' } },
      { id: 's2-2', from: 'staff', at: '2026-11-09T09:40:00+09:00', text: { ko: '예약 가능한 날짜를 확인해 드릴게요. 원하시는 요일을 알려 주세요.', en: "We'll check available dates for you. Which day of the week works best?" } },
      { id: 's2-3', from: 'user', at: '2026-11-09T10:15:00+09:00', booking: { date: '2026-11-16', time: '10:30', language: 'zh-TW', status: 'pending' } },
    ],
  },
  {
    hospitalId: 'sample-suseongview',
    name: { ko: '수성뷰 성형외과', en: 'Suseong View Plastic Surgery' },
    dept: 'plastic',
    district: '수성구',
    unread: 0,
    sample: true,
    messages: [
      { id: 's3-1', from: 'user', at: '2026-11-07T16:30:00+09:00', text: { ko: '수술 전 상담도 가능할까요?', en: 'Is a pre-surgery consultation possible?' } },
      { id: 's3-2', from: 'staff', at: '2026-11-07T17:10:00+09:00', text: { ko: '네, 원장님 상담은 내원하셔서 진행됩니다. 방문 희망 날짜를 알려 주세요.', en: "Yes, the consultation with the doctor takes place at the clinic. Let us know when you'd like to visit." } },
      { id: 's3-3', from: 'user', at: '2026-11-07T17:30:00+09:00', booking: { date: '2026-11-12', time: '15:00', language: 'en', status: 'cancelled', cancelledAt: '2026-11-10T09:00:00+09:00' } },
    ],
  },
  {
    hospitalId: 'sample-dongseongro',
    name: { ko: '동성로맑은 안과', en: 'Dongseongro Clear Eye Clinic' },
    dept: 'ophthalmology',
    district: '중구',
    unread: 0,
    sample: true,
    messages: [
      { id: 's4-1', from: 'user', at: '2026-11-05T11:00:00+09:00', text: { ko: '라식 수술 비용이 궁금합니다.', en: "I'd like to know the cost of LASIK surgery." } },
      { id: 's4-2', from: 'staff', at: '2026-11-05T13:20:00+09:00', text: { ko: '비용은 검사 결과에 따라 달라서, 내원 검사 후 정확히 안내해 드립니다.', en: 'The cost depends on your eye exam, so we will give you an exact estimate after the exam at the clinic.' } },
      { id: 's4-3', from: 'user', at: '2026-11-05T13:40:00+09:00', booking: { date: '2026-11-06', time: '10:00', language: 'en', status: 'confirmed', bookingNo: 'DC-261105-002', treatment: { ko: '라식 사전 검사', en: 'LASIK pre-exam' } } },
    ],
  },
];
