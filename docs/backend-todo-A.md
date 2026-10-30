# backend-todo-A.md — 백엔드 A 할 일 (환자 쪽 · 로그인)

> 작성 2026-10-30 · [backend-plan.md](backend-plan.md) v2, [backend-roles.md](backend-roles.md), [backend-contracts.md](backend-contracts.md)에서 A 몫만 뽑음
> 끝난 항목은 `[x]`로 바꾸고, 자세한 내용은 [backend-worklog-A.md](backend-worklog-A.md)에

## 한눈에

| 기간 | 목표 | 완료 기준 |
|---|---|---|
| ~11/4 | 기반 + 약속 확정 | 서버 실행, JWT 발급·검증, contracts 확정 |
| 11/5~8 | **로그인 → 요청서 제출** | 11/9 시연 흐름에서 환자 쪽 동작 |
| 11/10~16 | 병원 찾기 API | 목록·필터·거리 정렬·상세·가격 통계 |
| 11/17~23 | 알림·남용 방지 | 상태 변경 알림, 횟수 제한 |
| 11/24~30 | 챗봇 API·탈퇴 | pgvector 검색, 탈퇴·파기 |
| 12/1~7 | 통합 | OpenAPI 최종, 시연 리허설 |

## ~11/4 · 기반 (B와 같이)

- [ ] B와 `docs/backend-contracts.md` 초안 확정 (상태 코드, 토큰, 에러 코드, 함수 10개, `BookingCreate`)
- [ ] `proposed` 거절 후 상태 결정 → `backend-decisions.md`
- [ ] `backend/src/main.py`, `core/` 구조 같이 잡기 (B: `db.py`, A: `security.py`)
- [ ] `core/security.py`: JWT 발급·검증, `current_patient()`·`current_staff()` 의존성
- [ ] `core/errors.py`: `{code, message, detail}` 형식 (같이)
- [ ] 로컬에서 `docker compose up` + 서버 실행, `GET /api/v1/health` 확인 (B가 compose 준비)

## 11/5~8 · 로그인 → 요청서 (11/9 시연)

**auth (로그인)**
- [ ] `POST /auth/patient/code` — 이메일로 인증코드 발송 (데모: 콘솔 출력)
- [ ] `POST /auth/patient/verify` — 코드 확인 → 환자 토큰. 처음이면 계정 생성
- [ ] `login_codes`: 코드는 **해시로 저장**, 짧은 만료, 시도 횟수 제한 → `auth.code_invalid`, `auth.too_many_attempts`
- [ ] `POST /auth/staff/login` — 직원 비밀번호 로그인 → 직원 토큰(`tenant_id` 포함). 직원 계정 테이블은 B(`tenant`)
- [ ] 가입 시 "만 14세 이상" 확인 칸 (미만 가입 불가, 개인정보보호법 제22조의2)

**patient (계정)**
- [ ] `patients` 모델: 이메일·선호 언어·시간대·14세 확인·가입/탈퇴 시각만 (건강정보·이름 X)
- [ ] `GET /me`, `PATCH /me` (언어·시간대 변경)
- [ ] 로그인 전 브라우저에서 고른 언어를 가입 때 받아서 저장 (프론트와 약속)

**consent (동의)**
- [ ] `consents` 모델: 종류(`terms/privacy/health/overseas_transfer`)·문구 버전·언어·시각·철회
- [ ] `consent.service.record()`, `consent.service.require()` (B도 사용)
- [ ] 가입 시 `terms`·`privacy`, 요청서 제출 시 `health`(건강정보 칸 있을 때)·`overseas_transfer`(해외 LLM 쓸 때) **각각 따로**

**booking 환자용 router** (service는 B)
- [ ] `POST /hospitals/{id}/booking-requests` — 동의 확인 → `booking.service.create_request()` 호출
- [ ] `GET /me/booking-requests`, `GET /me/booking-requests/{id}` — 내 요청·상태·**승인된** 답장만
- [ ] `POST /me/booking-requests/{id}/accept`, `/cancel`

**테스트**
- [ ] 로그인 없이 제출 → 401
- [ ] 건강정보 있는데 `health` 동의 없음 → 422 `consent.required`
- [ ] 환자 A가 환자 B 요청 조회 → 404
- [ ] 인증코드 틀림·만료·시도 초과
- [ ] (교차) B 모듈: 환자 토큰으로 `confirm` → 403

**시연 확인 (B와)**
- [ ] 로그인 → 요청서 제출 → 병원 캘린더 "대기" → 병원 확정 → 내 요청에 "확정" 표시

## 11/10~16 · 병원 찾기

- [ ] `scripts/load_hospitals.py`: `data/interim/영업정보/` CSV → `hospitals`·`hospital_hours`·`hospital_departments` (4,242곳, 데이터 담당과)
- [ ] `GET /hospitals`: 필터(지역·진료과·요일·시간·휴진·등록·요청 가능), 정렬은 `distance`·`name`만 (그 외 422)
- [ ] `GET /hospitals/{id}`: 상세 + 진료시간 + `source`·`fetched_at` + 전화·이메일
- [ ] `hospital.service.get_basic()` (B가 대시보드에서 사용)
- [ ] `price_stats` 계산·적재 + `GET /prices/stats` (기관 5곳 미만 없음)
- [ ] `scripts/export_openapi.py` → `packages/shared-types` 첫 생성, 프론트와 점검

## 11/17~23 · 알림·남용 방지

- [ ] `notification.service.notify()` — 상태 변경 시 B가 호출, 데모는 콘솔
- [ ] 요청서 제출 횟수 제한(계정·IP), 같은 병원 미처리 요청 중복 → `booking.duplicate`

## 11/24~30 · 챗봇·탈퇴

- [ ] `POST /chatbot/ask` — `ai/chatbot` 호출 래퍼, 출처·기준일 포함, 횟수 제한 (AI 담당과)
- [ ] `chatbot_chunks` + pgvector 검색 연결
- [ ] `DELETE /me` 탈퇴 + 보관 기간 지난 요청 삭제·익명화 스크립트 (기간은 질의 회신 후)

## 12/1~7 · 통합

- [ ] 통합 테스트, OpenAPI → `shared-types` 최종
- [ ] 시연 시나리오 리허설 (가상 데이터만)

## B에게 받아야 하는 것

| 무엇 | 필요한 때 |
|---|---|
| `docker-compose.yml`, `core/db.py`, 첫 마이그레이션 | ~11/4 |
| `booking.service` 함수 5개 (`create_request` 등) | 11/5~8 초반 |
| 직원 계정 테이블(`staff_users`) | 직원 로그인 만들 때 |
| 내 모델 변경의 마이그레이션 생성 | 모델 바꿀 때마다 (PR로 요청) |

## 매번 지킬 것 (backend/AGENTS.md 요약)

- 브랜치 `backend-A-<기능>` → `backend`로 PR → B 리뷰
- B 파일은 고치지 않고 worklog "B에게 요청"에
- 세션 끝날 때 `backend-worklog-A.md` 맨 위에 기록
- 실명·실제 환자 정보·API 키 X, `.env` 커밋 X
