# backend-todo-B.md — 백엔드 B 할 일 (병원 쪽 · 예약 상태)

> 작성 2026-10-30 · [backend-plan.md](backend-plan.md) v2, [backend-roles.md](backend-roles.md), [backend-contracts.md](backend-contracts.md)에서 B 몫만 뽑음
> 끝난 항목은 `[x]`로 바꾸고, 자세한 내용은 [backend-worklog-B.md](backend-worklog-B.md)에

## 한눈에

| 기간 | 목표 | 완료 기준 |
|---|---|---|
| ~11/4 | 기반 + 약속 확정 | `docker compose up` + 서버 실행, `GET /api/v1/health`, 첫 마이그레이션, contracts 확정 |
| 11/5~8 | **요청서 상태 흐름 → 병원 확정** | 11/9 시연 흐름에서 병원 쪽 동작 |
| 11/10~16 | 가용 시간·격리 | `availability`, tenant 격리 의존성, 직원 계정 관리 |
| 11/17~23 | AI 답장·승인·기록 | 답장 초안 → 직원 승인 → 환자 언어로 표시, `audit` |
| 11/24~30 | 구독·사용량 | `subscription`·`usage` 목업, `llm_usage` 기록 |
| 12/1~7 | 통합 | 통합 테스트, 시연 데이터 정리 |

## ~11/4 · 기반 (A와 같이)

- [ ] A와 `docs/backend-contracts.md` 초안 확정 (상태 코드, 토큰, 에러 코드, 함수 10개, `BookingCreate`)
- [ ] `proposed` 거절 후 상태 결정 → `backend-decisions.md`
- [ ] 팀원 PC Docker Desktop 가능 여부 확인 (안 되면 공용 호스팅 DB, 가상 데이터만)
- [ ] 루트 `docker-compose.yml`: `pgvector/pgvector` 이미지, `CREATE EXTENSION vector;`
- [ ] `backend/src/main.py`, `core/` 구조 같이 잡기 (B: `db.py`, A: `security.py`)
- [ ] `core/config.py`: 환경변수(DB URL 등), `.env.example`에 항목 추가
- [ ] `core/db.py`: SQLAlchemy 2 엔진·세션, `get_db()` 의존성, 시간은 `timestamptz`(UTC)
- [ ] `core/errors.py`: `{code, message, detail}` 형식 (같이)
- [ ] `backend/alembic/` 초기화 + 첫 마이그레이션 (`vector` 확장 포함) — **마이그레이션 파일은 B만 생성**
- [ ] `GET /api/v1/health` (DB 연결 확인 포함)
- [ ] 테스트 DB 방식 정하기 (별도 DB 또는 트랜잭션 롤백) + `backend/tests/` 기본 설정
- [ ] 브랜치 이름 규칙 수정 PR: `backend/B-*`는 `backend` 브랜치와 충돌해 git이 거부 → `backend-B-*` (roles 4절, AGENTS.md 3절, decisions 8번)

## 11/5~8 · 요청서 상태 흐름 (11/9 시연)

**booking 모델 (주인 B)**
- [ ] `booking_requests`: patient_id, hospital_id, 상태(기본 `pending`), 언어, 국적, 연락 방법, 희망 날짜 후보(UTC, 1~3개), 진료과, 비자 필요 여부, 자유 입력(원문·번역), 건강정보(선택), 환자 시간대, 생성 시각
- [ ] `booking_events`: 이전→다음 상태, 행위자(환자 id / 직원 id), 제안 시간, 시각 (**지우지 않음**)
- [ ] `replies`: 종류, 한국어 원문, 번역문, AI 초안 여부, 승인 직원, 발송 시각 (승인 없으면 환자에게 안 보임)

**booking.service (A가 호출하는 함수, contracts 5절)**
- [ ] `create_request(db, patient_id, hospital_id, data)` → `BookingOut`
- [ ] `list_for_patient(db, patient_id)` → 승인된 답장만 포함
- [ ] `get_for_patient(db, patient_id, request_id)` → 남의 요청은 `not_found`
- [ ] `patient_accept()` (`proposed` → `confirmed`), `patient_cancel()` (`pending`·`proposed` → `cancelled`)
- [ ] 상태 전이 규칙을 service 한 곳에: 흐름에 없는 변경 → 409 `booking.invalid_transition`
- [ ] 모든 상태 변경은 `booking_events`에 기록 + `notification.service.notify()` 호출 (A 함수)

**booking 병원용 router**
- [ ] `GET /tenant/booking-requests?from=&to=&status=` — 캘린더·문의함, **내 병원 것만**
- [ ] `GET /tenant/booking-requests/{id}` — 상세 (원문+번역)
- [ ] `POST /tenant/booking-requests/{id}/confirm`, `/reject`, `/propose`

**tenant (최소)**
- [ ] `tenants`: hospital_id, 등록번호, 플랜, 요청 기능 on/off (**등록 유치의료기관만 on**)
- [ ] `staff_users`: tenant_id, 이메일, 비밀번호 해시, 역할(`owner/staff`) — A의 직원 로그인이 사용
- [ ] 병원용 API는 `current_staff()`의 `tenant_id`로만 조회

**seed_demo.py**
- [ ] 가상 병원 3곳(`is_demo=true`)·직원 계정·가상 요청 (환자 쪽 가상 데이터는 A가 PR)

**테스트**
- [ ] 환자 토큰으로 `confirm` → 403
- [ ] 병원 A 직원이 병원 B 요청 조회 → 404
- [ ] 흐름에 없는 상태 변경 → 409
- [ ] 상태 변경마다 `booking_events` 1건씩
- [ ] (교차) A 모듈: 환자 A가 환자 B 요청 조회 → 404

**시연 확인 (A와)**
- [ ] 로그인 → 요청서 제출 → 병원 캘린더 "대기" → 병원 확정 → 환자 화면에 "확정" 표시

## 11/10~16 · 가용 시간·격리

- [ ] `availability`: 요일·시간대 또는 날짜별 슬롯, `GET·PUT /tenant/availability`
- [ ] tenant 격리 공통 의존성 정리 (모든 `/tenant/...`에 적용)
- [ ] 직원 계정 관리 (owner가 staff 추가·비활성)
- [ ] `hospital.service.get_basic()`(A 함수)로 대시보드 병원 정보 표시
- [ ] `shared-types` 첫 생성 후 병원 대시보드 프론트와 API 점검

## 11/17~23 · AI 답장·승인·기록

- [ ] `POST /tenant/booking-requests/{id}/reply-draft` — AI 답장 초안 (발송 X)
- [ ] `POST /tenant/replies/{id}/approve` — 직원 승인 → 환자 계정 언어로 번역 → 표시
- [ ] 번역·요약·시간 제안은 `BackgroundTasks`로 (요청서 제출이 멈추지 않게)
- [ ] LLM 호출은 `ai/llm/client.py`만 (마스킹), 도구 로직은 `ai/agent` (AI 담당과 호출 방식 맞추기)
- [ ] `audit_logs` + `audit.service.log_action()`, `GET /tenant/audit-logs`
- [ ] 테스트: 미승인 답장은 환자 API에 안 보임

## 11/24~30 · 구독·사용량

- [ ] `subscription` 플랜·좌석 (목업)
- [ ] `llm_usage` 기록 (tenant 또는 `platform`, 서비스, 토큰), `GET /tenant/usage`
- [ ] 교차 테스트: A 모듈의 권한·격리 테스트 작성

## 12/1~7 · 통합

- [ ] 통합 테스트
- [ ] 시연 데이터 정리 (가상 데이터만), 시연 시나리오 리허설

## A에게 받아야 하는 것

| 무엇 | 필요한 때 |
|---|---|
| `core/security.py` — `current_staff()` (토큰의 `tenant_id`) | ~11/4 |
| 직원 로그인 `POST /auth/staff/login` | 11/5~8 |
| `consent.service.require()` | 요청서 생성 흐름 |
| `notification.service.notify()` | 상태 변경 알림 |
| `hospital.service.get_basic()` | 대시보드 병원 정보 |
| A 모델 변경 PR (마이그레이션은 B가 생성) | A가 모델 바꿀 때마다 |

## 매번 지킬 것 (backend/AGENTS.md 요약)

- 브랜치 `backend-B-<기능>` → `backend`로 PR → A 리뷰
- A 파일은 고치지 않고 worklog "A에게 요청"에
- 마이그레이션 PR은 하루 1~2개로 모으고, 머지 전 `alembic upgrade head` 확인
- 세션 끝날 때 `backend-worklog-B.md` 맨 위에 기록
- 실명·실제 환자 정보·API 키 X, `.env` 커밋 X
