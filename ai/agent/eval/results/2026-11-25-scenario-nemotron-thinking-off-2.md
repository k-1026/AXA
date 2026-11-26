# 원스톱 시나리오 (서비스 층 경유) — 2026-11-25 nemotron-thinking-off-2

확인 항목 통과 4 / 6
> 사용한 모델: [('nemotron', 'private/nvidia/nemotron-3.5-super-120b-a12b')]. 가상 데이터. 대화는 저장소의 텍스트만으로 이어 감. 제출은 기존 예약 요청 API 호출을 코드가 대신함

턴별 (초 / LLM 호출): [('scar', 2.5, 2), ('recommend', 0.9, 2), ('residency', 1.9, 2), ('book', 2.1, 2), ('nationality', 0.5, 1), ('visa', 1.5, 2)] · 합계 호출 11회, 입력 토큰 53929

| 결과 | 확인 항목 | 메모 |
|---|---|---|
| O | 1. 병원 목록·추천 카드가 나왔다 | {'scar': ['hospital_list'], 'recommend': [], 'residency': [], 'book': [], 'nationality': [], 'visa': []} |
| X | 2. 체류 형태는 사용자가 말한 뒤에만 저장됐다 | {'scar': None, 'recommend': None, 'residency': None, 'book': None, 'nationality': None, 'visa': None} |
| X | 3. 요청서 초안 카드가 나왔다 | {'scar': ['hospital_list'], 'recommend': [], 'residency': [], 'book': [], 'nationality': [], 'visa': []} |
| O | 4. 챗봇은 제출하지 않았다 (내 요청 0건) |  |
| O | 5. 저장소에는 사용자·챗봇 텍스트만 있다 | 12개 |
| O | 12. 다른 계정의 세션 접근(이어 쓰기·삭제)은 거절되고 내 세션은 남는다 | ['ask=404 not_found', 'delete=404 not_found'], 내 세션 남음=True |

## 대화 기록

**사용자:** I have acne scars and want treatment in Suseong-gu. I only speak English.

- 카드: ['hospital_list']
- 저장된 상태: 체류 형태=None, 초안 있음=False, 보여 준 병원=[9001, 9002]

**챗봇:** I found two dermatology clinics in Suseong-gu with English support:

1. **Demo Dermatology Clinic A** — staff speak English, AI translation chat available
2. **Demo Dermatology Clinic B** — staff speak English and Chinese, AI translation chat available

Would you like me to recommend one of these for acne scar treatment, or would you prefer to pick one yourself?

**사용자:** Please recommend one for me. I'd like to go on December 4th.

- 카드: []
- 저장된 상태: 체류 형태=None, 초안 있음=False, 보여 준 병원=[9001, 9002]

**챗봇:** Are you visiting Korea short-term, or do you live in Korea (alien registration / NHIS)?

**사용자:** I'm just visiting Korea for a week.

- 카드: []
- 저장된 상태: 체류 형태=None, 초안 있음=False, 보여 준 병원=[9001, 9002]

**챗봇:** I need to record your residency status first. Are you visiting Korea short-term, or do you live in Korea (alien registration / NHIS)?

**사용자:** Let's book the first one on December 4 at 10:00. I want to ask about scar laser options.

- 카드: []
- 저장된 상태: 체류 형태=None, 초안 있음=False, 보여 준 병원=[9001, 9002]

**챗봇:** Are you visiting Korea short-term, or do you live in Korea (alien registration / NHIS)?

**사용자:** I'm from Taiwan.

- 카드: []
- 저장된 상태: 체류 형태=None, 초안 있음=False, 보여 준 병원=[9001, 9002]

**챗봇:** I need to know your residency status — are you visiting Korea short-term, or do you live in Korea (alien registration / NHIS)?

**사용자:** No, I don't need help with a visa.

- 카드: []
- 저장된 상태: 체류 형태=None, 초안 있음=False, 보여 준 병원=[9001, 9002]

**챗봇:** Are you visiting Korea short-term, or do you live in Korea (alien registration / NHIS)?

