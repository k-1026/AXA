# backend-contracts.md — 백엔드 A·B 사이의 약속

> **초안** (2026-10-30). 11/4 전에 A·B가 같이 확정 → 그 뒤 변경은 **별도 PR + 상대 승인** + 맨 아래 변경 이력
> 이 파일에 없는 방식으로 상대 모듈을 부르지 않는다. 근거: [backend-plan.md](backend-plan.md), [backend-roles.md](backend-roles.md)

## 1. 파일 주인

| 경로 | 주인 | 상대가 고칠 때 |
|---|---|---|
| `backend/src/core/` | A+B 공동 | PR + 상대 승인 |
| `backend/alembic/` | A | 마이그레이션 생성은 A만 (결정 13) |
| `modules/auth/`, `patient/`, `consent/`, `hospital/`, `price/`, `chatbot/`, `notification/`, `fx/`, `maintenance/` | A | 요청만 |
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
| `sid` | 로그인 세션 id (`auth_sessions.id`) | 없음 (직원도 필요하면 B가 같은 방식으로) |
| `exp` | 만료 시각 | 만료 시각 |

- 발급: A(`auth`). 검증 의존성(`core/security.py`): `current_patient()`, `current_staff()` — 병원 API는 `current_staff()`로 받은 `tenant_id`로만 조회
- `current_patient()`는 요청마다 DB에서 세션 확인: 로그아웃·만료·탈퇴(계정 삭제)면 401 `auth.required` → **로그아웃하면 그 토큰은 바로 못 씀** (`POST /auth/patient/logout`, 다른 기기 세션은 유지)

## 4. 에러 형식·코드

```json
{"code": "booking.invalid_transition", "message": "…", "detail": {}}
```

| code | HTTP | 언제 |
|---|---|---|
| `auth.required` | 401 | 로그인 필요 |
| `auth.forbidden` | 403 | 역할이 다름 (환자 토큰으로 병원 API 등) |
| `auth.invalid_credentials` | 401 | 이메일 또는 비밀번호가 맞지 않음 (어느 쪽인지 알려주지 않음) |
| `auth.email_taken` | 409 | 이미 가입된 이메일 |
| `auth.too_many_attempts` | 429 | 로그인·탈퇴 비밀번호 실패 초과: 이메일당 15분 5회, IP당 15분 20회 (`detail.retry_after` 초). 성공하면 그 이메일 기록 초기화. 지금은 서버 메모리 → 운영 전 공유 저장소로 |
| `not_found` | 404 | 없거나 **내 것이 아님** (남의 데이터는 403 대신 404) |
| `api.not_found` | 404 | **API 경로 자체가 없음** (오타·배포 버전 어긋남). `not_found`와 일부러 나눔: 프론트는 `not_found`를 "서버에 이미 없음"으로 보고 화면에서 지우는 곳이 있음 |
| `api.method_not_allowed` | 405 | 경로는 있지만 그 메서드가 없음 (`Allow` 헤더 그대로) |
| `validation` | 422 | 입력 오류 |
| `consent.required` | 422 | 필수 동의 없음 |
| `booking.invalid_transition` | 409 | 상태 흐름에 없는 변경 |
| `booking.duplicate` | 409 | 같은 병원에 처리 안 된 요청이 이미 있음 |
| `rate_limited` | 429 | 제출 횟수 초과 · 챗봇 호출 초과(`detail.limit` = `minute`/`day`/`sessions`, `detail.retry_after` 초) |
| `fx.unavailable` | 503 | 환율을 받지 못했고 저장된 값도 없음 |
| `chatbot.unavailable` | 503 | 모든 LLM 제공자가 실패 (대화는 저장하지 않음, 잠시 뒤 다시) |
| `db.unavailable` | 503 | `GET /health`에서 DB 연결 실패 (`DATABASE_URL` 없음 포함, 로그에는 예외 종류만) |
| `internal` | 500 | 처리하지 못한 서버 오류 (`detail` = `{}`, 로그에는 예외 종류만) |

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

- 챗봇(A)도 `booking.service.list_for_patient`·`get_for_patient`를 부른다 — "내 요청 상태" 답과 제출 확인용, `modules/chatbot/bookings.py` 한 곳에서만. `booking` 모듈이 올라오기 전에는 "요청 없음"으로 동작

## 6. 요청서 입력 (`BookingCreate`, 초안)

| 칸 | 타입 | 필수 | 비고 |
|---|---|---|---|
| `department_code` | str | O | 진료과 코드 = `departments.code` (`dermatology`, `plastic`, `internal`, `ophthalmology` …) |
| `preferred_slots` | list[datetime(UTC)] | O | 1~3개 |
| `patient_timezone` | str (IANA, 예 `Asia/Taipei`) | O | 화면 표시용 |
| `lang` | str (`ko`/`en`/`zh-TW`/`zh-CN`/`vi`) | O | 요청 언어 (`patients.preferred_lang`·프론트 번역과 같은 5개) |
| `nationality` | str (국가 코드) | O | |
| `contact_method` | str (`email`/…) | O | |
| `visa_needed` | bool | O | |
| `message` | str | X | 자유 입력 원문 → 번역은 백그라운드 |
| `health_info` | str | X | 있으면 `health` 동의 필수 |
| `consents` | list[{kind, version}] | O | `privacy` 필수, `health`·`overseas_transfer` 조건부 |
| `residency` | str (`short_term`) | **제안** | 체류 형태. 국내 거주 외국인은 유치 대상이 아니라 요청 불가(의료법 제27조 제3항 제2호) → 지금은 챗봇 안에서만 거름(자기 신고). 사람이 쓰는 요청서에도 같은 확인이 필요해 칸 또는 계정 속성으로 추가 제안 — **B 확인 필요** |

- 요청서의 `privacy` 동의 = **이 요청서 내용을 고른 병원에 전달**하는 데 대한 동의 (가입 때 `privacy`와 별개로 요청서마다). 법적 구조가 제3자 제공(개인정보보호법 제17조 제1항 제1호)인지 처리 위탁(제26조)인지는 **개인정보위 질의 8번 회신 후** 문구 확정 ([plan.md](../subject/plan.md) 11절)

## 7. 챗봇 API (A, `modules/chatbot/`, 결정 16)

모두 **환자 로그인 필요**. 경로 앞 `/api/v1`. 응답 모델은 `ai/agent/schemas.py`(카드 형식의 기준) → OpenAPI

| 메서드·경로 | 하는 일 | 에러 |
|---|---|---|
| `POST /chatbot/ask` | `{session_id?, message(1~1000자), language?}` → `{session_id, text, cards[], ai_generated, blocked, medical_notice}`. `session_id`가 없으면 새 대화, `language`가 없으면 계정 선호 언어 | 404 `not_found`(남의·없는 대화), 422 `validation`, 429 `rate_limited`, 503 `chatbot.unavailable` |
| `GET /chatbot/sessions?limit=` | 내 대화 목록 `[{id, title, lang, created_at, last_message_at}]`, 최근 순, 최대 50 | — |
| `GET /chatbot/sessions/{id}` | 한 대화 + `messages[{role, content, refused, created_at}]` (개인정보를 가린 글만) | 404 `not_found` |
| `DELETE /chatbot/sessions/{id}` | 대화 삭제 → 204 | 404 `not_found` |

- **언어**: `ko`, `en`, `zh-TW`, `zh-CN`, `vi`. 별칭 `zh`·`zh-Hans`→`zh-CN`, `zh-Hant`→`zh-TW`. 그 밖은 422
- **카드** `{type, data}` 9종: `hospital_list`, `hospital_suggestions`, `hospital_detail`, `price_list`, `sources`, `time_slots`, `booking_draft`, `booking_list`, `aftercare_thread`. 숫자·병원 정보는 도구 결과에서 코드가 넣음
- **요청서 카드**(`booking_draft`)의 `data.request`는 6절 `BookingCreate` 모양(희망 일시 UTC). 프론트 [제출] = `POST /hospitals/{hospital_id}/booking-requests`에 `request` + 환자가 체크한 `consents`(`data.consents_required` 목록)를 그대로. **챗봇 전용 제출 경로 없음**
- **진료과**: 챗봇은 한국어 이름을 받아 `department_code`로 바꿈. 코드 표에 없는 진료과는 병원 찾기까지만, 요청서 불가
- **저장**: 개인정보를 가린 대화 글 + 상태(체류 형태, 초안 일부, 보여 준 병원)만. 도구 결과·카드·초안의 `health_info`·`message`는 저장 X → 지난 대화를 열면 글만 보임. 30일 후 삭제, 탈퇴 즉시 삭제
- **호출 제한**: 계정당 분 10회·일 150회(가정), 계정당 대화 50개. 지금은 서버 메모리 → 운영 전 DB·캐시로

## 7-1. 내부 정리 API (A, `modules/maintenance/`)

| 메서드·경로 | 하는 일 | 에러 |
|---|---|---|
| `GET`·`POST /internal/purge` | 30일 지난 챗봇 대화 + 만료·로그아웃한 로그인 세션 삭제 → `{chat_sessions, auth_sessions}` (지운 수) | 404 `not_found`(`CRON_SECRET` 없음 = 꺼짐), 401 `auth.required`(비밀 값 틀림) |

- 인증: `Authorization: Bearer <CRON_SECRET>` (환경변수 `CRON_SECRET`, 16자 이상). Swagger에 숨김
- **예약 작업이 하루 1번 불러야 함** (Vercel Cron 등). 부르지 않으면 30일 보관 정리가 되지 않음. Vercel Cron은 GET + 이 헤더를 자동으로 보냄 (`vercel.json` 설정은 배포 담당이)

## 8. 변경 이력

| 날짜 | 절 | 바뀐 것 | 누가 (A/B) | PR |
|---|---|---|---|---|
| 2026-11-12 | 4 | 에러 `api.not_found`(404)·`api.method_not_allowed`(405) 추가 (없는 경로·메서드도 같은 형식, 리소스 없음 `not_found`와 구분), `db.unavailable`(503) 추가 — `GET /health`가 DB 연결도 확인, 응답 `{"status":"ok","db":"ok"}` | B (**A 확인 필요**) | `backend-B-health-404` → `backend` |
| 2026-11-12 | 1·7-1 | 내부 정리 API `/internal/purge`(`CRON_SECRET`), 새 모듈 `maintenance/`(A) | A (**B 확인 필요**) | `backend-review-fix` → `backend` |
| 2026-11-12 | 4 | 가입 동의 `terms`·`privacy`는 현재 문서 버전(프론트 `features/legal` `updated`, 지금 `2026-11-03`)만 받음 → 아니면 422 `validation` + `detail.invalid[{kind, version, current}]` | A | `backend-review-fix` → `backend` |
| 2026-11-12 | 4 | `auth.too_many_attempts` 구현 (로그인·`DELETE /me` 비밀번호 확인) | A (**B 확인 필요**) | `backend-review-fix` → `backend` |
| 2026-11-12 | 4 | 에러 `internal`(500) 추가 (처리하지 못한 예외도 같은 형식) | A (**B 확인 필요**) | `backend-review-fix` → `backend` |
| 2026-11-11 | 4·5·6·7 | 챗봇 API 7절 신설(`/chatbot/ask`, `/chatbot/sessions` 목록·상세·삭제), 에러 `chatbot.unavailable`(503)·`rate_limited`에 챗봇 호출 추가, 챗봇의 `booking.service` 호출, `BookingCreate.lang` 5개 언어·`department_code` 값, `residency` 칸 제안 | A (**B 확인 필요**) | `backend-A-chatbot` → `backend` |
| 2026-11-04 | 1·4 | 새 모듈 `fx/`(A, 환율), 에러 `fx.unavailable`(503). `DELETE /me` 탈퇴(비밀번호 확인) | A | — |
| 2026-11-05 | — | `DELETE /me` 탈퇴 = 계정 즉시 삭제(결정 15). 응답·코드는 그대로 | A | — |
| 2026-11-04 | 3 | 환자 토큰에 `sid` 추가, `current_patient()`가 DB 세션 확인 (로그아웃 즉시 무효) | A (B 확인 필요) | — |
| 2026-11-04 | 1 | `backend/alembic/` 주인 B → A, `docker-compose.yml` 삭제 (Supabase 사용) | A (B 확인 필요) | — |
| 2026-11-04 | 4 | 입력 오류(FastAPI 기본 422)도 `{code: "validation", …, detail.errors}` 형식으로. `auth.code_invalid` 삭제(인증코드 로그인 안 함), `auth.invalid_credentials`·`auth.email_taken` 추가. 가입 시 14세·필수 동의 없으면 `consent.required` + `detail.age14_confirmed`·`missing` | A (B 확인 필요) | — |
| 2026-10-30 | 전체 | 초안 작성 | — | — |
