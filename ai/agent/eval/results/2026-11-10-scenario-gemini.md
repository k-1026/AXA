# 원스톱 시나리오 (서비스 층 경유) — 2026-11-10 gemini

확인 항목 통과 10 / 10
> 사용한 모델: [('gemini', 'gemini-3.5-flash'), ('gemini', 'gemini-3.5-flash-lite')]. 가상 데이터. 대화는 저장소의 텍스트만으로 이어 감. 제출은 기존 예약 요청 API 호출을 코드가 대신함

턴별 (초 / LLM 호출): [('scar', 4.9, 3), ('recommend', 9.7, 2), ('residency', 10.9, 2), ('book', 4.7, 3), ('nationality', 3.0, 2), ('visa', 25.8, 2), ('status1', 8.3, 1), ('status2', 3.1, 2)] · 합계 호출 17회, 입력 토큰 62457

| 결과 | 확인 항목 | 메모 |
|---|---|---|
| O | 1. 병원 목록·추천 카드가 나왔다 | {'scar': ['hospital_list'], 'recommend': [], 'residency': ['hospital_suggestions'], 'book': [], 'nationality': [], 'visa': ['booking_draft']} |
| O | 2. 체류 형태는 사용자가 말한 뒤에만 저장됐다 | {'scar': None, 'recommend': None, 'residency': 'short_term', 'book': 'short_term', 'nationality': 'short_term', 'visa': 'short_term'} |
| O | 3. 요청서 초안 카드가 나왔다 | {'scar': ['hospital_list'], 'recommend': [], 'residency': ['hospital_suggestions'], 'book': [], 'nationality': [], 'visa': ['booking_draft']} |
| O | 4. 챗봇은 제출하지 않았다 (내 요청 0건) |  |
| O | 5. 저장소에는 사용자·챗봇 텍스트만 있다 | 12개 |
| O | 6. 초안이 사용자 말과 맞다 (첫 번째 병원, 12/4 10:00, 대만, 비자 도움 없음) | 병원=9002(첫 번째=9002) request={'department_code': 'dermatology', 'preferred_slots': ['2026-12-04T01:00:00Z'], 'lang': 'en', 'nationality': 'TW', 'visa_needed': False} |
| O | 7. 동의가 모자라면 같은 API가 거절한다 | consent.required |
| O | 8. 같은 API로 제출하면 pending 요청이 생긴다 | demo-bk-new-001 |
| O | 9. 다음 대화에서 제출을 알아보고 초안을 닫았다 (pending으로 답함) | 초안 남음=False, 상태 카드=None, 답변에 pending=True |
| O | 10. 병원 확정 후 상태 질문에 confirmed로 답했다 | ['confirmed'] |

## 대화 기록

**사용자:** I have acne scars and want treatment in Suseong-gu. I only speak English.

- 카드: ['hospital_list']
- 저장된 상태: 체류 형태=None, 초안 있음=False, 보여 준 병원=[9001, 9002]

**챗봇:** For acne scars, dermatology (피부과) is typically visited. Here are the Dermatology clinics in Suseong-gu with English support:

1. **Demo Dermatology Clinic A** (English-speaking staff, AI translation chat)
2. **Demo Dermatology Clinic B** (English and Chinese-speaking staff, AI translation chat)

Which of these clinics would you like to visit, or would you like a recommendation?

**사용자:** Please recommend one for me. I'd like to go on December 4th.

- 카드: []
- 저장된 상태: 체류 형태=None, 초안 있음=False, 보여 준 병원=[9001, 9002]

**챗봇:** Are you visiting Korea short-term, or do you live in Korea (alien registration / NHIS)?

**사용자:** I'm just visiting Korea for a week.

- 카드: ['hospital_suggestions']
- 저장된 상태: 체류 형태=short_term, 초안 있음=False, 보여 준 병원=[9002, 9001]

**챗봇:** Based on your English support needs, location in Suseong-gu, and preferred date of December 4th, I suggest **Demo Dermatology Clinic B** (staff speak English, has consultation slots on that date) or **Demo Dermatology Clinic A**. 

*(This suggestion is based on matching conditions like language support and schedule. MediDaegu may receive a referral fee.)*

Would you like to book a consultation at one of these clinics?

**사용자:** Let's book the first one on December 4 at 10:00. I want to ask about scar laser options.

- 카드: []
- 저장된 상태: 체류 형태=short_term, 초안 있음=False, 보여 준 병원=[9002, 9001]

**챗봇:** What is your nationality (country), and do you need visa-related document assistance from the hospital?

**사용자:** I'm from Taiwan.

- 카드: []
- 저장된 상태: 체류 형태=short_term, 초안 있음=False, 보여 준 병원=[9002, 9001]

**챗봇:** Do you need visa-related document assistance from the hospital?

**사용자:** No, I don't need help with a visa.

- 카드: ['booking_draft']
- 저장된 상태: 체류 형태=short_term, 초안 있음=True, 보여 준 병원=[9002, 9001]

**챗봇:** I have prepared a consultation request draft for **Demo Dermatology Clinic B** on December 4, 2026, at 10:00. 

Please check the summary card, review and tick the required consents, and press **Submit**. The hospital will confirm your appointment afterwards.

**[프론트가 기존 예약 요청 API로 제출]** 동의=['privacy', 'overseas_transfer'] → demo-bk-new-001 (pending)

**사용자:** Did my request go through?

- 카드: []
- 저장된 상태: 체류 형태=short_term, 초안 있음=False, 보여 준 병원=[9002, 9001]

**챗봇:** Yes, your request to Demo Dermatology Clinic B has been sent and is currently pending. The hospital will confirm, decline, or propose another time, and you can check the status here at any time.

**[병원 직원이 대시보드에서 확정]**

**사용자:** Any update from the hospital?

- 카드: ['booking_list']
- 저장된 상태: 체류 형태=short_term, 초안 있음=False, 보여 준 병원=[9002, 9001]

**챗봇:** Your consultation at Demo Dermatology Clinic B has been **confirmed** for December 4, 2026, at 10:00.

