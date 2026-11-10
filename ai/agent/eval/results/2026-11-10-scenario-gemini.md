# 원스톱 시나리오 — 2026-11-10 gemini

확인 항목 통과 10 / 10
> 사용한 모델: [('gemini', 'gemini-3.5-flash-lite')]. 가상 데이터. 제출·병원 확정은 코드가 대신함

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
| O | 9. 병원 확정 후 상태 질문에 다시 조회했다 | ['get_my_bookings'] |
| O | 10. 저장소 상태가 confirmed |  |

## 대화 기록

**사용자:** I have acne scars and want treatment in Suseong-gu. I only speak English.

- 호출한 도구: ['suggest_department', 'search_hospitals']
- 카드: ['hospital_list']
- 초안 있음: False · 체류 형태 기록: None

**챗봇:** Acne scars are typically treated in Dermatology (피부과) or Plastic Surgery (성형외과). 

Here are the registered dermatology clinics in Suseong-gu offering English support:

1. **Demo Dermatology Clinic A**
2. **Demo Dermatology Clinic B**

Would you like to search prices for acne scar treatments or select one of these clinics for a consultation request?

**사용자:** Please recommend one for me. I'd like to go on December 4th.

- 호출한 도구: ['recommend_hospitals']
- 카드: []
- 초안 있음: False · 체류 형태 기록: None

**챗봇:** Are you visiting Korea short-term, or do you live in Korea (alien registration / NHIS)?

**사용자:** I'm just visiting Korea for a week.

- 호출한 도구: ['record_residency', 'recommend_hospitals']
- 카드: ['hospital_suggestions']
- 초안 있음: False · 체류 형태 기록: short_term

**챗봇:** Based on English staff availability and opening on December 4th, I suggest **Demo Dermatology Clinic B** (staff speak English and Chinese, open on Friday). *Suggestions are based solely on matching your conditions (language, schedule, location). MediDaegu may receive a referral fee from the hospital.*

Would you like to prepare a consultation request for Demo Dermatology Clinic B?

**사용자:** Let's book the first one on December 4 at 10:00. I want to ask about scar laser options.

- 호출한 도구: ['prepare_booking_request']
- 카드: []
- 초안 있음: False · 체류 형태 기록: short_term

**챗봇:** Do you need help from the hospital with visa paperwork?

**사용자:** I'm from Taiwan.

- 호출한 도구: ['prepare_booking_request']
- 카드: []
- 초안 있음: False · 체류 형태 기록: short_term

**챗봇:** Do you need help from the hospital with visa paperwork? (Yes or No)

**사용자:** No, I don't need help with a visa.

- 호출한 도구: ['prepare_booking_request']
- 카드: ['booking_draft']
- 초안 있음: True · 체류 형태 기록: short_term

**챗봇:** Please check the consultation request summary card, tick the required consents, and press Submit. The hospital will confirm your appointment afterwards.

**[환자가 제출 버튼을 누름]** → [Submitted] The consultation request to Demo Dermatology Clinic B was submitted (id demo-bk-new-001, status: pending). The hospital will confirm, decline, or propose another time.

**사용자:** Did my request go through?

- 호출한 도구: ['get_my_bookings']
- 카드: ['booking_list']
- 초안 있음: False · 체류 형태 기록: short_term

**챗봇:** Yes, your request to Demo Dermatology Clinic B is currently pending. The hospital will review it and confirm, decline, or propose another time. You can check the status here anytime.

**[병원 직원이 대시보드에서 확정]**

**사용자:** Any update from the hospital?

- 호출한 도구: ['get_my_bookings']
- 카드: ['booking_list']
- 초안 있음: False · 체류 형태 기록: short_term

**챗봇:** Your request has been confirmed for December 4, 2026, at 10:00.

