# 원스톱 시나리오 (서비스 층 경유) — 2026-11-10 nemotron

확인 항목 통과 10 / 10
> 사용한 모델: [('nemotron', 'private/nvidia/nemotron-3.5-super-120b-a12b')]. 가상 데이터. 대화는 저장소의 텍스트만으로 이어 감. 제출은 기존 예약 요청 API 호출을 코드가 대신함

턴별 (초 / LLM 호출): [('scar', 5.1, 3), ('recommend', 3.1, 2), ('residency', 5.5, 3), ('book', 8.5, 2), ('nationality', 27.3, 2), ('visa', 2.0, 1), ('status1', 13.8, 2), ('status2', 1.9, 3)] · 합계 호출 18회, 입력 토큰 82539

| 결과 | 확인 항목 | 메모 |
|---|---|---|
| O | 1. 병원 목록·추천 카드가 나왔다 | {'scar': ['hospital_list'], 'recommend': [], 'residency': ['hospital_suggestions'], 'book': [], 'nationality': ['booking_draft'], 'visa': []} |
| O | 2. 체류 형태는 사용자가 말한 뒤에만 저장됐다 | {'scar': None, 'recommend': None, 'residency': 'short_term', 'book': 'short_term', 'nationality': 'short_term', 'visa': 'short_term'} |
| O | 3. 요청서 초안 카드가 나왔다 | {'scar': ['hospital_list'], 'recommend': [], 'residency': ['hospital_suggestions'], 'book': [], 'nationality': ['booking_draft'], 'visa': []} |
| O | 4. 챗봇은 제출하지 않았다 (내 요청 0건) |  |
| O | 5. 저장소에는 사용자·챗봇 텍스트만 있다 | 12개 |
| O | 6. 초안이 사용자 말과 맞다 (첫 번째 병원, 12/4 10:00, 대만, 비자 도움 없음) | 병원=9002(첫 번째=9002) request={'department_code': 'dermatology', 'preferred_slots': ['2026-12-04T01:00:00Z'], 'lang': 'en', 'nationality': 'TW', 'visa_needed': False} |
| O | 7. 동의가 모자라면 같은 API가 거절한다 | consent.required |
| O | 8. 같은 API로 제출하면 pending 요청이 생긴다 | demo-bk-new-001 |
| O | 9. 다음 대화에서 제출을 알아보고 초안을 닫았다 (pending으로 답함) | 초안 남음=False, 상태 카드=['pending'], 답변에 pending=True |
| O | 10. 병원 확정 후 상태 질문에 confirmed로 답했다 | ['confirmed'] |

## 대화 기록

**사용자:** I have acne scars and want treatment in Suseong-gu. I only speak English.

- 카드: ['hospital_list']
- 저장된 상태: 체류 형태=None, 초안 있음=False, 보여 준 병원=[9001, 9002]

**챗봇:** Acne scars are typically handled by dermatology (피부과) — a doctor will decide the suitable treatment at your consultation.

Here are the registered dermatology clinics in Suseong-gu with English support:

1. **Demo Dermatology Clinic A** (가상피부과의원 A) — Suseong-gu
   - Staff languages: English
   - AI translation chat: Yes
   - Registered foreign-patient facility: Yes

2. **Demo Dermatology Clinic B** (가상피부과의원 B) — Suseong-gu
   - Staff languages: English, Chinese
   - AI translation chat: Yes
   - Registered foreign-patient facility: Yes

Would you like more details on one of these (address, phone, hours), or would you like to send a consultation request to a specific clinic?

**사용자:** Please recommend one for me. I'd like to go on December 4th.

- 카드: []
- 저장된 상태: 체류 형태=None, 초안 있음=False, 보여 준 병원=[9001, 9002]

**챗봇:** Before I can suggest clinics, I need to know: are you visiting Korea short-term, or do you live in Korea (alien registration / NHIS)?

**사용자:** I'm just visiting Korea for a week.

- 카드: ['hospital_suggestions']
- 저장된 상태: 체류 형태=short_term, 초안 있음=False, 보여 준 병원=[9002, 9001]

**챗봇:** Based on your conditions (English-speaking staff, Suseong-gu, available on December 4th), here are the suggestions:

1. **Demo Dermatology Clinic B** — staff speak English, consultation slots available on 2026-12-04, located in Suseong-gu
2. **Demo Dermatology Clinic A** — staff speak English, located in Suseong-gu

These suggestions are based on how well each hospital matches your stated conditions (language, location, available date) — not on medical quality or results. All are registered foreign-patient facilities. MediDaegu is a registered patient facilitator and may receive a referral fee from hospitals; the fee does not affect the order.

Which clinic would you like to send a consultation request to?

**사용자:** Let's book the first one on December 4 at 10:00. I want to ask about scar laser options.

- 카드: []
- 저장된 상태: 체류 형태=short_term, 초안 있음=False, 보여 준 병원=[9002, 9001]

**챗봇:** I need one more detail before the request can be prepared: what is your nationality (country)?

**사용자:** I'm from Taiwan.

- 카드: ['booking_draft']
- 저장된 상태: 체류 형태=short_term, 초안 있음=True, 보여 준 병원=[9002, 9001]

**챗봇:** A draft consultation request has been prepared for **Demo Dermatology Clinic B** (dermatology) on **December 4 at 10:00**, in English, asking about scar laser options.

Please check the summary card next to this message, tick the required consents (privacy and overseas transfer), and press **Submit**. The hospital will then confirm, decline, or propose another time.

**사용자:** No, I don't need help with a visa.

- 카드: []
- 저장된 상태: 체류 형태=short_term, 초안 있음=True, 보여 준 병원=[9002, 9001]

**챗봇:** Got it — no visa paperwork needed. That's already reflected in the draft.

Please check the summary card next to this message, tick the required consents (privacy and overseas transfer), and press **Submit**. The hospital will then confirm, decline, or propose another time.

**[프론트가 기존 예약 요청 API로 제출]** 동의=['privacy', 'overseas_transfer'] → demo-bk-new-001 (pending)

**사용자:** Did my request go through?

- 카드: ['booking_list']
- 저장된 상태: 체류 형태=short_term, 초안 있음=False, 보여 준 병원=[9002, 9001]

**챗봇:** Yes, your request was sent to **Demo Dermatology Clinic B** for **December 4 at 10:00**. The status is **pending**, meaning the hospital will confirm, decline, or propose another time. You can check the status here anytime.

**[병원 직원이 대시보드에서 확정]**

**사용자:** Any update from the hospital?

- 카드: ['booking_list']
- 저장된 상태: 체류 형태=short_term, 초안 있음=False, 보여 준 병원=[9002, 9001]

**챗봇:** Great news — your consultation request has been **confirmed**!

- **Hospital:** Demo Dermatology Clinic B
- **Date & time:** December 4, 2026 at 10:00
- **Status:** Confirmed

The hospital has accepted your requested slot. You're all set for your acne scar laser consultation. Is there anything else you'd like help with?

