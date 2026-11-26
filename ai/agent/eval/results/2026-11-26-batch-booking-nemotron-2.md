# 예약 칸 한 번에 묻기 (nemotron-2)

모델: ['nvidia/nemotron-3.5-super-vl-120b-a12b', 'nvidia/nemotron-3.5-lightning-30b-a3b'] · 4/4 · 턴별 초: [('search', 78.7), ('pick', 31.2), ('answer', 25.5)]

| 결과 | 확인 항목 | 메모 |
|---|---|---|
| O | 1. 병원을 고른 턴에서 빠진 칸을 한 메시지에 물었다 (5칸 중 4칸 이상) | 물은 칸=['date', 'language', 'nationality', 'visa', 'inquiry'] |
| O | 2. 2턴에서 초안을 미리 만들지 않았다 (값을 지어내지 않음) | [] |
| O | 3. 한 줄 답 뒤에 바로 초안 카드가 나왔다 (3턴 만에) | ['booking_draft'] |
| O | 4. 초안이 사용자 말과 맞다 (첫 번째 병원, 12/4 10:00, 영어, 대만, 비자 도움 없음) | 병원=9001(첫 번째=9001) {'preferred_slots': ['2026-12-04T01:00:00Z'], 'lang': 'en', 'nationality': 'TW', 'visa_needed': False} |

## 대화

**사용자:** I have acne scars and want treatment in Suseong-gu.

- 카드: ['hospital_list'] · 78.7초

**챗봇:** Here are two dermatology clinics in Suseong-gu that support English:

1. **Demo Dermatology Clinic A** — staff language: English; AI translation chat available. Tel: 053-000-0001
2. **Demo Dermatology Clinic B** — staff languages: English, Chinese; AI translation chat available. Tel: 053-000-0002

Both are registered to treat foreign patients. Would you like to book a consultation at one of them, or would you like me to check prices for acne scar treatment?

**사용자:** I'm just visiting Korea for a week. Let's book the first one.

- 카드: [] · 31.2초

**챗봇:** Please reply with all of these in one line:

1. Preferred date and time (up to 3 options)
2. Language you want for the consultation
3. Your nationality (country name)
4. Do you want the hospital to help with visa paperwork? (yes/no, in your own words)
5. What you'd like to ask at the consultation

**사용자:** December 4 at 10:00, in English, I'm from Taiwan, no visa help needed, and I want to ask about scar laser options.

- 카드: ['booking_draft'] · 25.5초

**챗봇:** Your consultation request draft is ready for **Demo Dermatology Clinic A** (dermatology) on **December 4 at 10:00**, in English, with your inquiry about scar laser options.

Please check the summary card, tick the required consents (privacy, health, overseas transfer), and press **Submit**. The hospital will confirm afterwards — I can't say it's booked yet.
