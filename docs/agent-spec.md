# agent-spec.md — 에이전트가 할 수 있는 일 / 하면 안 되는 일

> 근거: `subject/plan.md` 4절, `docs/compliance.md`, `research/의료관광/규제-예약요청-캘린더.md`

| 에이전트 | 할 수 있는 일 | 하면 안 되는 일 | 도구 |
|---|---|---|---|
| 환자 쪽 입력 도우미 (`web-platform/booking-request`) | 요청서 칸 채우기 도움, 번역, 빠진 정보(날짜·연락처·비자) 알려주기 | 병원 고르기, 시술 추천, 증상 판단, 환자 대신 제출 | `translate` |
| 병원 쪽 요청 정리 (`ai/agent`) | 요청서 요약·번역, 답장 초안, 예약 가능 시간 제안 | 자동 확정, 의료 판단, 가격 흥정, 직원 승인 없는 답장 발송 | `summarize_request`, `translate`, `draft_reply`, `schedule` |
| 정보 챗봇 (`ai/chatbot`) | 공공 문서 검색 → 출처·기준일과 함께 답 | 학습 지식만으로 답, 특정 병원 추천, 증상·시술 판단 | retriever |

## 공통 규칙
- 숫자(진료시간·가격)는 코드가 데이터에서 그대로 넣고, LLM은 문장만 작성
- 모든 작업은 `automation-log`에 기록 (무엇을, 누가 승인했는지)
- 거절 문구 예: "의료진 판단이 필요한 질문입니다. 요청서에 적어 병원에 직접 물어보세요."
- 시나리오 테스트는 `ai/agent/eval`, `ai/chatbot/eval`에 (거절해야 하는 질문 포함)
