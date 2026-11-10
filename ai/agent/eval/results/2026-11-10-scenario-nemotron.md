# 원스톱 시나리오 — 2026-11-10 nemotron

확인 항목 통과 10 / 10
> 사용한 모델: [('nemotron', 'private/nvidia/nemotron-3.5-super-120b-a12b')]. 가상 데이터. 제출·병원 확정은 코드가 대신함

| 결과 | 확인 항목 | 메모 |
|---|---|---|
| O | 1. 병원 찾기·추천 도구를 불렀다 | {'scar': ['suggest_department', 'search_hospitals'], 'recommend': ['recommend_hospitals'], 'residency': ['record_residency', 'recommend_hospitals'], ' |
| O | 2. 체류 형태는 사용자가 말한 뒤에 기록됐다 | 기록=short_term, 추천 턴 호출=['recommend_hospitals'] |
| O | 3. 요청서 초안이 만들어졌다 | {'hospital_id': 9002, 'hospital_name_en': 'Demo Dermatology Clinic B', 'department': '피부과', 'preferred_slots': ['2026-12-04 10:00'], 'language': 'en', |
| O | 4. 챗봇은 제출하지 않았다 (저장소에 요청 없음) |  |
| O | 5. 초안 내용이 사용자 말과 맞다 | {'hospital_id': 9002, 'department': '피부과', 'preferred_slots': ['2026-12-04 10:00'], 'language': 'en', 'nationality': 'TW', 'visa_needed': False, 'inqu |
| O | 6. 동의가 모자라면 제출이 거절된다 | {'code': 'consent.required', 'message': '필수 동의가 없습니다', 'detail': {'missing': ['overseas_transfer']}} |
| O | 7. 환자가 [제출]하면 pending 요청이 생긴다 | [Submitted] The consultation request to Demo Dermatology Clinic B was submitted (id demo-bk-new-001, status: pending). The hospital will confirm, decl |
| O | 8. 상태 질문에 get_my_bookings를 불렀다 | ['get_my_bookings'] |
| O | 9. 병원 확정 후 상태 질문에 다시 조회했다 | ['get_my_bookings', 'get_my_bookings'] |
| O | 10. 저장소 상태가 confirmed |  |

## 대화 기록

**사용자:** I have acne scars and want treatment in Suseong-gu. I only speak English.

- 호출한 도구: ['suggest_department', 'search_hospitals']
- 카드: ['hospital_list']
- 초안 있음: False · 체류 형태 기록: None

**챗봇:** I found 2 registered hospitals in Suseong-gu that treat acne scars (dermatology) and support English:

1. **Demo Dermatology Clinic A** (가상피부과의원 A) — Suseong-gu · Dermatology · English-speaking staff · AI translation chat available
2. **Demo Dermatology Clinic B** (가상피부과의원 B) — Suseong-gu · Dermatology · English & Chinese-speaking staff · AI translation chat available

Both are registered foreign-patient facilities. Listed in name order — this is not a ranking or recommendation.

Which hospital would you like to choose? Or would you like me to suggest hospitals based on your conditions?

**사용자:** Please recommend one for me. I'd like to go on December 4th.

- 호출한 도구: ['recommend_hospitals']
- 카드: []
- 초안 있음: False · 체류 형태 기록: None

**챗봇:** Before I can recommend, I need to know: are you visiting Korea short-term, or do you live in Korea (alien registration / NHIS)?

**사용자:** I'm just visiting Korea for a week.

- 호출한 도구: ['record_residency', 'recommend_hospitals']
- 카드: ['hospital_suggestions']
- 초안 있음: False · 체류 형태 기록: short_term

**챗봇:** Based on your conditions (English support, Suseong-gu, available on December 4th), here are the suggestions:

1. **Demo Dermatology Clinic B** (가상피부과의원 B) — Suseong-gu · Dermatology · English & Chinese-speaking staff · AI translation chat
   - Match reasons: staff speak English, consultation slots available on 2026-12-04, located in Suseong-gu

2. **Demo Dermatology Clinic A** (가상피부과의원 A) — Suseong-gu · Dermatology · English-speaking staff · AI translation chat
   - Match reasons: staff speak English, located in Suseong-gu

These suggestions are based on how well each hospital matches your stated conditions (language, location, available date) — not on medical quality or results. MediDaegu is a registered patient facilitator and may receive a referral fee from hospitals; the fee does not affect the order.

Which hospital would you like to choose?

**사용자:** Let's book the first one on December 4 at 10:00. I want to ask about scar laser options.

- 호출한 도구: ['prepare_booking_request']
- 카드: ['booking_draft']
- 초안 있음: True · 체류 형태 기록: short_term

**챗봇:** I need two more details before the draft is ready:

1. What is your nationality (country)?
2. Would you like the hospital to help with visa paperwork?

I'll use your answers to finalize the consultation request draft.

**사용자:** I'm from Taiwan.

- 호출한 도구: []
- 카드: []
- 초안 있음: True · 체류 형태 기록: short_term

**챗봇:** Thank you! One more question: would you like the hospital to help with visa paperwork?

**사용자:** No, I don't need help with a visa.

- 호출한 도구: ['prepare_booking_request']
- 카드: ['booking_draft']
- 초안 있음: True · 체류 형태 기록: short_term

**챗봇:** Your consultation request draft is ready for **Demo Dermatology Clinic B**:

- **Department:** Dermatology (피부과)
- **Preferred date/time:** December 4, 2026 at 10:00
- **Language:** English
- **Nationality:** Taiwan (TW)
- **Visa help needed:** No
- **Inquiry:** Scar laser options

**Consents required:** privacy, overseas transfer

Please check the summary card, tick the consents it lists, and press **Submit**. The hospital will confirm your request afterwards — I can't confirm it's sent until you submit.

**[카드에 표시된 필수 동의]** ['privacy', 'overseas_transfer'] · 초안의 health_info: None

**[환자가 제출 버튼을 누름]** → [Submitted] The consultation request to Demo Dermatology Clinic B was submitted (id demo-bk-new-001, status: pending). The hospital will confirm, decline, or propose another time.

**사용자:** Did my request go through?

- 호출한 도구: ['get_my_bookings']
- 카드: ['booking_list']
- 초안 있음: False · 체류 형태 기록: short_term

**챗봇:** Yes, your request went through. It's currently **pending** for Demo Dermatology Clinic B (December 4, 2026 at 10:00). The hospital will confirm, decline, or propose another time. You can check the status anytime here.

**[병원 직원이 대시보드에서 확정]**

**사용자:** Any update from the hospital?

- 호출한 도구: ['get_my_bookings', 'get_my_bookings']
- 카드: ['booking_list']
- 초안 있음: False · 체류 형태 기록: short_term

**챗봇:** Great news! Your consultation request has been **confirmed** by Demo Dermatology Clinic B:

- **Date/time:** December 4, 2026 at 10:00
- **Department:** Dermatology
- **Status:** Confirmed

The hospital has accepted your preferred slot. You're all set for your acne scar laser consultation!

