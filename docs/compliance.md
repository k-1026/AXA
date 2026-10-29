# compliance.md — 서비스 경계 (개발 기준)

> 근거: `research/의료관광/규제-*.md`, `서비스-흐름-법률검토.md` · 상세 계획: `subject/plan.md` 5절
> 법적 판단이 아니라 조문·판례에 비춘 설계 기준. 기관 질의 회신(2026-10-29 접수) 후 갱신

## 한다 / 하지 않는다

| 한다 | 하지 않는다 |
|---|---|
| 공공데이터 기반 병원·진료시간·공공 가격 열람 (출처·기준일 표시) | 병원에서 입점비·광고비·예약 건당 수수료 받기 |
| 병원 연락처·홈페이지·지도 링크 | 예약 대행, 초청장 발급, 통역 동행, 픽업 |
| 공식 등록·인증 사실 표시 | 순위, "추천", "최저가", 후기, 전후 사진 |
| 기준일·출처, "광고·추천·의료 상담 아님" 고지 | 이벤트 할인가·할인율 노출, 크롤링 가격 |
| 환자가 고른 병원 1곳에 예약 **요청서** 전달 (확정은 병원) | 사후관리 Q&A, 시술 후 의료 안내 메시지 |
| 원문 그대로 번역 (원문·번역문 병기) | 번역에 요약·의역·추천 덧붙이기 |

## 코드에서 지킬 규칙

| 규칙 | 적용 위치 |
|---|---|
| 목록 정렬은 거리·가나다순만. 구독·"온라인 요청 가능" 여부는 필터일 뿐 정렬에 반영 X | `backend/modules/hospital`, `web-platform/hospital·map` |
| 예약 상태 기본값 = `pending`. `confirmed`는 병원 직원 계정만 | `backend/modules/booking`, `web-hospital/calendar` |
| 요청 기능은 등록 유치의료기관만 켤 수 있음 | `backend/modules/tenant` |
| 병원 상세에 전화·이메일 등 다른 접수 경로 항상 표시 (특정 앱 단독 접수 X, 의료법 제15조) | `web-platform/hospital` |
| 건강정보(희망 진료·증상)는 선택 입력 + **별도 동의** (개인정보보호법 제23조) | `web-platform/booking-request` |
| 병원 데이터는 해당 병원(tenant)만 조회·집계 (제26조 제5항) | `backend/modules/tenant`, `web-hospital/analytics` |
| LLM 호출 전 개인정보 마스킹, 데모는 가상 데이터만 (국외 이전, 제28조의8) | `ai/llm/safety.py` |
| 증상·시술 판단, 병원 추천 요청은 거절 → 병원 문의로 안내 (의료법 제27조 제1항) | `ai/llm/safety.py`, `ai/chatbot/prompts`, `ai/*/eval` |
| 답장은 직원 승인 후 발송. 자동 발송은 접수 확인 메시지만 | `ai/agent/workflows`, `web-hospital/agent-settings` |
| 구독 요금 기준 = 기능·좌석·AI 사용량. 예약 건수·환자 수·진료비 기준 X | `backend/modules/subscription` |
| 광고(애드센스)는 목록·상세 옆에만, 건강·미용 카테고리 차단. 요청서·동의·챗봇 화면엔 X | `apps/web-platform` |

## 출처
- 의료법: https://www.law.go.kr/법령/의료법
- 의료 해외진출 및 외국인환자 유치 지원에 관한 법률: https://www.law.go.kr/법령/의료해외진출및외국인환자유치지원에관한법률
- 개인정보 보호법: https://www.law.go.kr/법령/개인정보보호법
- 대법원 2018도20928: https://www.law.go.kr/LSW/precInfoP.do?precSeq=207141
