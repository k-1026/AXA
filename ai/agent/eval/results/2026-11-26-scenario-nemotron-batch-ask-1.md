# 원스톱 시나리오 (서비스 층 경유) — 2026-11-26 nemotron-batch-ask-1

확인 항목 통과 12 / 12
> 사용한 모델: [('nemotron', 'private/nvidia/nemotron-3.5-super-120b-a12b')]. 가상 데이터. 대화는 저장소의 텍스트만으로 이어 감. 제출은 기존 예약 요청 API 호출을 코드가 대신함

턴별 (초 / LLM 호출): [('scar', 42.4, 3), ('recommend', 17.0, 2), ('residency', 26.8, 3), ('book', 43.5, 2), ('nationality', 10.4, 1), ('visa', 36.4, 2), ('status1', 1.3, 1), ('status2', 28.4, 2)] · 합계 호출 16회, 입력 토큰 84153

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
| O | 11. 서버에 저장된 초안에 health_info·inquiry가 없다 (화면 카드의 request.message에는 문의 내용이 있다) | 저장된 초안 1번, 허용 밖 키=[], 카드 message(문의) 있음=True |
| O | 12. 다른 계정의 세션 접근(이어 쓰기·삭제)은 거절되고 내 세션은 남는다 | ['ask=404 not_found', 'delete=404 not_found'], 내 세션 남음=True |

## 대화 기록

**사용자:** I have acne scars and want treatment in Suseong-gu. I only speak English.

- 카드: ['hospital_list']
- 저장된 상태: 체류 형태=None, 초안 있음=False, 보여 준 병원=[9001, 9002]

**챗봇:** Acne scars are usually handled by dermatology (and sometimes plastic surgery). A doctor will decide the right treatment at your consultation.

Here are two registered hospitals in Suseong-gu with English support:

1. **Demo Dermatology Clinic A** (가상피부과의원 A) — English-speaking staff, AI translation chat available. Tel: 053-000-0001
2. **Demo Dermatology Clinic B** (가상피부과의원 B) — English and Chinese-speaking staff, AI translation chat available. Tel: 053-000-0002

Would you like me to help you send a consultation request to one of these hospitals? If so, please let me know which one.

**사용자:** Please recommend one for me. I'd like to go on December 4th.

- 카드: []
- 저장된 상태: 체류 형태=None, 초안 있음=False, 보여 준 병원=[9001, 9002]

**챗봇:** I can recommend a hospital for you, but first I need to know: are you visiting Korea short-term, or do you live in Korea (alien registration / NHIS)?

**사용자:** I'm just visiting Korea for a week.

- 카드: ['hospital_suggestions']
- 저장된 상태: 체류 형태=short_term, 초안 있음=False, 보여 준 병원=[9002, 9001]

**챗봇:** Here are two hospitals that match your conditions (English support, Suseong-gu, available on December 4th):

1. **Demo Dermatology Clinic B** — staff speak English and Chinese, AI translation chat available, consultation slots on Dec 4, located in Suseong-gu. Tel: 053-000-0002
2. **Demo Dermatology Clinic A** — staff speak English, AI translation chat available, located in Suseong-gu. Tel: 053-000-0001

These suggestions are based on how well each hospital matches your stated conditions (language, opening day, location). This is not a judgment of medical quality. MediDaegu is a registered patient facilitator and may receive a referral fee from hospitals; the fee does not affect the order.

Which one would you like to choose for a consultation request?

**사용자:** Let's book the first one on December 4 at 10:00. I want to ask about scar laser options.

- 카드: []
- 저장된 상태: 체류 형태=short_term, 초안 있음=False, 보여 준 병원=[9002, 9001]

**챗봇:** Almost ready — I just need two more details:

1. Your nationality (country name)
2. Do you want the hospital to help with visa paperwork? (Please answer in your own words, e.g. "yes" or "no, I don't need it")

You can answer both in one line.

**사용자:** I'm from Taiwan.

- 카드: []
- 저장된 상태: 체류 형태=short_term, 초안 있음=False, 보여 준 병원=[9002, 9001]

**챗봇:** One more question: do you want the hospital to help with visa paperwork? Please answer in your own words (e.g. "yes" or "no, I don't need it").

**사용자:** No, I don't need help with a visa.

- 카드: ['booking_draft']
- 저장된 상태: 체류 형태=short_term, 초안 있음=True, 보여 준 병원=[9002, 9001]

**챗봇:** Your consultation request draft is ready for **Demo Dermatology Clinic B** (dermatology) on **December 4 at 10:00**, in English, with your inquiry about scar laser options.

Please check the summary card, tick the required consents (**privacy** and **overseas transfer**), and press **Submit**. The hospital will confirm afterwards — I can't say it's booked until you submit.

**[프론트가 기존 예약 요청 API로 제출]** 동의=['privacy', 'overseas_transfer'] → demo-bk-new-001 (pending)

**사용자:** Did my request go through?

- 카드: []
- 저장된 상태: 체류 형태=short_term, 초안 있음=False, 보여 준 병원=[9002, 9001]

**챗봇:** Yes, your request to Demo Dermatology Clinic B was sent and is now **pending**. The hospital will confirm, decline, or propose another time. You can check the status here anytime.

**[병원 직원이 대시보드에서 확정]**

**사용자:** Any update from the hospital?

- 카드: ['booking_list']
- 저장된 상태: 체류 형태=short_term, 초안 있음=False, 보여 준 병원=[9002, 9001]

**챗봇:** Great news — the hospital confirmed your appointment:

- **Demo Dermatology Clinic B**
- **December 4, 2026 at 10:00**
- Status: Confirmed

You're all set. Is there anything else you'd like help with?

