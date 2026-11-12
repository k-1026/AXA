import type { AftercareMessage } from './types';

// 데모 계정용 예시 사후 관리 대화 (방문 완료 예약 id → 대화). 실제 진료 기록이 아니다
export const SAMPLE_AFTERCARE: Record<string, { messages: AftercareMessage[]; unread: number }> = {
  's1-0': {
    unread: 1,
    messages: [
      { id: 'a1-1', from: 'doctor', at: '2026-11-04T10:00:00+09:00', text: { ko: '어제 시술 받으신 부위는 2~3일 정도 붉은기가 남을 수 있어요. 자외선 차단제를 꼭 발라 주세요.', en: 'Some redness may remain for 2–3 days after yesterday’s treatment. Please make sure to use sunscreen.' } },
      { id: 'a1-2', from: 'user', at: '2026-11-05T21:10:00+09:00', text: { ko: '오늘도 볼 쪽에 붉은기가 조금 남아 있는데 괜찮을까요?', en: 'There is still a little redness on my cheeks today. Is that okay?' } },
      { id: 'a1-3', from: 'doctor', at: '2026-11-06T09:30:00+09:00', text: { ko: '지금 상태를 사진으로 보내 주시면 확인해 드릴게요. 밝은 곳에서 정면으로 찍어 주세요.', en: 'Please send a photo of the area so we can check. Take it facing forward in good light.' } },
    ],
  },
};
