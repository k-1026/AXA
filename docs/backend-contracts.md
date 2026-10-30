# backend-contracts.md — 백엔드 A·B 사이의 약속

> **초안** (2026-10-30). 11/4 전에 A·B가 같이 확정 → 그 뒤 변경은 **별도 PR + 상대 승인** + 맨 아래 변경 이력
> 이 파일에 없는 방식으로 상대 모듈을 부르지 않는다. 근거: [backend-plan.md](backend-plan.md), [backend-roles.md](backend-roles.md)

## 1. 파일 주인

| 경로 | 주인 | 상대가 고칠 때 |
|---|---|---|
| `backend/src/core/` | A+B 공동 | PR + 상대 승인 |
| `docker-compose.yml`, `backend/alembic/` | B | 마이그레이션 생성은 B만 |
| `modules/auth/`, `patient/`, `consent/`, `hospital/`, `price/`, `chatbot/`, `notification/` | A | 요청만 |
| `modules/booking/models.py`, `booking/service.py` | B | 요청만 |
| `modules/booking/router_patient.py` | A | — |
| `modules/booking/router_tenant.py` | B | — |
| `modules/tenant/`, `agent/`, `audit/`, `subscription/` | B | 요청만 |
| `scripts/load_hospitals.py`, `export_openapi.py` | A | — |
| `scripts/seed_demo.py` | B | 환자 쪽 가상 데이터는 A가 PR |
| `backend/tests/` | 각자 자기 모듈 + 상대 모듈의 권한·격리 테스트 | — |
| `backend/AGENTS.md`, `docs/backend-contracts.md`, `docs/backend-decisions.md` | A+B 공동 | PR + 상대 승인 |
| `docs/backend-worklog-A.md` / `-B.md` | A / B | 고치지 않음 |

## 2. 예약 요청 상태 코드

| 코드 | 뜻 | 누가 바꾸나 |
|---|---|---|
| `pending` | 대기 (기본값) | 생성 시 |
| `confirmed` | 확정 | 병원 직원 / 환자가 `proposed` 수락 |
| `rejected` | 거절 | 병원 직원 |
| `proposed` | 병원이 다른 시간 제안 | 병원 직원 |
| `cancelled` | 환자 취소 | 환자 (`pending`·`proposed`에서만) |
| `expired` | 희망 날짜가 모두 지남 | 시스템 |

- 미정: 환자가 `proposed`를 거절하면? (`backend-decisions.md`에 결정되면 여기 반영)

## 3. 토큰 (JWT)

| 칸 | 환자 | 직원 |
|---|---|---|
| `sub` | patient id | staff id |
| `role` | `patient` | `staff` |
| `tenant_id` | 없음 | 병원 tenant id |
| `exp` | 만료 시각 | 만료 시각 |

- 발급: A(`auth`). 검증 의존성(`core/security.py`): `current_patient()`, `current_staff()` — 병원 API는 `current_staff()`로 받은 `tenant_id`로만 조회

## 4. 에러 형식·코드

```json
{"code": "booking.invalid_transition", "message": "…", "detail": {}}
```

| code | HTTP | 언제 |
|---|---|---|
| `auth.required` | 401 | 로그인 필요 |
| `auth.forbidden` | 403 | 역할이 다름 (환자 토큰으로 병원 API 등) |
| `auth.code_invalid` | 400 | 인증코드 틀림·만료 |
| `auth.too_many_attempts` | 429 | 시도 초과 |
| `not_found` | 404 | 없거나 **내 것이 아님** (남의 데이터는 403 대신 404) |
| `validation` | 422 | 입력 오류 |
| `consent.required` | 422 | 필수 동의 없음 |
| `booking.invalid_transition` | 409 | 상태 흐름에 없는 변경 |
| `booking.duplicate` | 409 | 같은 병원에 처리 안 된 요청이 이미 있음 |
| `rate_limited` | 429 | 제출 횟수 초과 |

- `code`는 프론트 i18n 키로 그대로 씀. 새 코드는 이 표에 먼저 추가

## 5. 서로 호출하는 함수

> 이름·입력·출력만 약속. 내부 구현은 주인 마음. 타입은 `schemas.py`의 Pydantic 모델

| 함수 | 주인 | 호출하는 쪽 | 입력 → 출력 |
|---|---|---|---|
| `booking.service.create_request(db, patient_id, hospital_id, data: BookingCreate)` | B | A (환자 router) | → `BookingOut`. 동의 확인은 호출 전에 A가 |
| `booking.service.list_for_patient(db, patient_id)` | B | A | → `list[BookingOut]` (승인된 답장만 포함) |
| `booking.service.get_for_patient(db, patient_id, request_id)` | B | A | → `BookingOut` / 없으면 `not_found` |
| `booking.service.patient_accept(db, patient_id, request_id)` | B | A | → `BookingOut` |
| `booking.service.patient_cancel(db, patient_id, request_id)` | B | A | → `BookingOut` |
| `consent.service.require(db, patient_id, kinds: list[str], request_id=None)` | A | A·B | 없으면 `consent.required` |
| `consent.service.record(db, patient_id, kind, version, lang, request_id=None)` | A | A | → `ConsentOut` |
| `notification.service.notify(patient_id, event, payload)` | A | B (상태 변경 후) | 데모는 콘솔 출력 |
| `audit.service.log_action(db, tenant_id, actor, action, ref)` | B | A·B | 기록만 |
| `hospital.service.get_basic(db, hospital_id)` | A | B (대시보드 병원 정보) | → `HospitalBasic` |

## 6. 요청서 입력 (`BookingCreate`, 초안)

| 칸 | 타입 | 필수 | 비고 |
|---|---|---|---|
| `department_code` | str | O | 진료과 코드 |
| `preferred_slots` | list[datetime(UTC)] | O | 1~3개 |
| `patient_timezone` | str (IANA, 예 `Asia/Taipei`) | O | 화면 표시용 |
| `lang` | str (`en`/`zh-TW`/`vi`/`ko`) | O | 요청 언어 |
| `nationality` | str (국가 코드) | O | |
| `contact_method` | str (`email`/…) | O | |
| `visa_needed` | bool | O | |
| `message` | str | X | 자유 입력 원문 → 번역은 백그라운드 |
| `health_info` | str | X | 있으면 `health` 동의 필수 |
| `consents` | list[{kind, version}] | O | `privacy` 필수, `health`·`overseas_transfer` 조건부 |

- 요청서의 `privacy` 동의 = **이 요청서 내용을 고른 병원에 전달**하는 데 대한 동의 (가입 때 `privacy`와 별개로 요청서마다). 법적 구조가 제3자 제공(개인정보보호법 제17조 제1항 제1호)인지 처리 위탁(제26조)인지는 **개인정보위 질의 8번 회신 후** 문구 확정 ([plan.md](../subject/plan.md) 11절)

## 7. 변경 이력

| 날짜 | 절 | 바뀐 것 | 누가 (A/B) | PR |
|---|---|---|---|---|
| 2026-10-30 | 전체 | 초안 작성 | — | — |
