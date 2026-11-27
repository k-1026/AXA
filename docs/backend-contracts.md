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
| `confirmed` | 확정 | 병원 직원(`pending`에서만 — 환자가 고른 시간) / 환자가 `proposed` 수락 (병원이 제안한 시간은 병원이 확정 X, 결정 33) |
| `rejected` | 거절 | 병원 직원 |
| `proposed` | 병원이 다른 시간 제안 | 병원 직원 — 제안 시간은 그 병원 진료시간 안(휴진일·진료 전후·점심이면 422 `validation`, `loc: ["slot"]`; 진료시간 데이터 없으면 막지 않음, 결정 33) |
| `cancelled` | 환자 취소 | 환자 (`pending`·`proposed`에서만) |
| `expired` | 희망 날짜가 모두 지남 | 시스템 |

- 미정: 환자가 `proposed`를 거절하면? (`backend-decisions.md`에 결정되면 여기 반영)
- **거절 사유** (`POST /tenant/booking-requests/{id}/reject` 본문 `{"reason": …}`, 선택): `fully_booked`(예약 마감) · `not_offered`(하지 않는 진료) · `needs_consult`(대면 상담 필요) · `other`(기타). `booking_events.reason`에 코드로 저장(마이그레이션 없음), 환자 화면 문장은 프론트 i18n. 목록에 없는 코드 → 422 `validation`, 거절이 아닌 행동에 `reason` → 422

## 3. 토큰 (JWT)

| 칸 | 환자 | 직원 |
|---|---|---|
| `sub` | patient id | staff id |
| `role` | `patient` | `staff` |
| `tenant_id` | 없음 | 병원 tenant id |
| `sid` | 로그인 세션 id (`auth_sessions.id`) | 없음 (직원도 필요하면 B가 같은 방식으로) |
| `exp` | 만료 시각 | 만료 시각 |

- 발급: A(`auth`). 환자 `POST /auth/patient/signup`·`login`, 병원 관계자 `POST /auth/staff/signup`(입점 = 병원 계정 + 대표 직원 `owner`, 등록 유치기관·영업 중만 + 지금은 가상 병원(`is_demo`)만 — 실제 병원 403 `auth.signup_closed`(결정 34), `{email, password, hospital_id, registration_no, consents}`)·`POST /auth/staff/login` — **가입할 때 환자/병원을 나눔**. 직원 토큰은 세션 없음. 검증 의존성(`core/security.py`): `current_patient()`, `current_staff()` — 병원 API는 `current_staff()`로 받은 `tenant_id`로만 조회
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
| `auth.email_taken` | 409 | 이미 가입된 이메일 (환자·직원 각각) |
| `auth.hospital_taken` | 409 | 이미 입점한 병원 (병원 1곳 = 병원 계정 1개, 직원 가입 때) |
| `auth.signup_closed` | 403 | 아직 입점 신청을 받지 않는 병원 (지금은 시연용 가상 병원 `is_demo`만 가입, 결정 34) |
| `auth.too_many_attempts` | 429 | 로그인·탈퇴 비밀번호 실패 초과: 이메일당 15분 5회, IP당 15분 20회 (`detail.retry_after` 초). 성공하면 그 이메일 기록 초기화. 지금은 서버 메모리 → 운영 전 공유 저장소로 |
| `not_found` | 404 | 없거나 **내 것이 아님** (남의 데이터는 403 대신 404) |
| `validation` | 422 | 입력 오류 |
| `consent.required` | 422 | 필수 동의 없음 |
| `residency.required` | 422 | 계정에 체류 형태 답이 없음 → `PUT /me/residency` 먼저 (예약 요청 때, 결정 28) |
| `residency.not_eligible` | 403 | 국내 거주 외국인 → 상담·예약 요청 불가, 정보 열람만 (의료법 제27조 제3항 제2호, 결정 28) |
| `booking.invalid_transition` | 409 | 상태 흐름에 없는 변경 |
| `booking.duplicate` | 409 | (2026-11-26부터 안 씀 — 아래 시간 규칙으로 바뀜) |
| `booking.time_conflict` | 409 | 내 다른 살아 있는 예약(확인 대기·시간 제안·확정, 어느 병원이든) 시간 앞뒤 60분 안. `detail` = `request_id`·`hospital_id`·`slot`·`buffer_minutes` (docs/booking-rules.md) |
| `booking.same_day` | 409 | 같은 병원에 그날 살아 있는 예약(요청)이 이미 있음. `detail` = `request_id`·`date`(한국 날짜) |
| `booking.too_many` | 409 | 처리 전 요청(확인 대기·시간 제안)이 이미 5건. `detail.max` |
| `booking.patient_conflict` | 409 | (병원 쪽) 확정·제안하려는 시간이 그 환자의 다른 **확정** 예약과 60분 이내 → 다른 시간 제안. `detail`은 time_conflict와 같음 |
| `hospital.not_requestable` | 403 | 상담·예약 요청을 받을 수 없는 병원 (`can_request = false`: 유치의료기관 미등록 또는 폐업·영업 미확인). `detail.reason` = `unregistered`/`not_operating`/`not_joined`(등록 기관이지만 메디대구 입점 안 함 = tenant 없음·`requests_enabled=false`, 예약 요청 때만). 병원 정보 공개(목록·상세·챗봇)는 **등록 병원만** — 미등록 병원은 목록에 없고 상세는 404 `not_found` (결정 21) |
| `rate_limited` | 429 | 제출 횟수 초과 · 챗봇 호출 초과(`detail.limit` = `minute`/`day`/`sessions`, `detail.retry_after` 초) |
| `fx.unavailable` | 503 | 환율을 받지 못했고 저장된 값도 없음 |
| `storage.unavailable` | 503 | 사진·영상 저장소(Supabase Storage)를 쓸 수 없음 — 설정 없음·Supabase 오류 (결정 22) |
| `push.unavailable` | 503 | 웹 푸시 VAPID 키가 없음 → 화면은 사이트 안 알림만 (결정 30) |
| `realtime.unavailable` | 503 | 실시간 알림 토큰을 만들 수 없음 (`SUPABASE_URL`·`SUPABASE_JWT_SECRET` 없음) → 화면은 주기 확인 (결정 27) |
| `chatbot.unavailable` | 503 | 모든 LLM 제공자가 실패 (대화는 저장하지 않음, 잠시 뒤 다시) |
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
| `notification.service.notify(db, patient_id, kind, request_id, status=None)` | A | B (상태 변경·답장, **commit 전**) | `kind` = status·reply·aftercare. commit하지 않음 → 부르는 쪽 commit에 같이 (결정 27) |
| `audit.service.log_action(db, tenant_id, actor, action, ref)` | B | A·B | 기록만 |
| `hospital.service.get_basic(db, hospital_id)` | A | B (대시보드 병원 정보) | → `HospitalBasic`(`id`, `ykiho`, `name_ko`, `name_en`, `type_code`, `sggu`, `addr_ko`, `tel`, `is_registered_facility`, `is_demo`, `can_request`) / 없으면 `not_found` |
| `hospital.service.require_requestable(db, hospital_id)` | A | A (요청서 제출 전) | → `HospitalBasic` / 미등록·영업 중 아님이면 403 `hospital.not_requestable` (`detail.reason` = `unregistered`/`not_operating`), 없으면 `not_found` |

- **요청 가능 병원**: `POST /hospitals/{id}/booking-requests`는 `booking.service.create_request()`를 부르기 **전에** A가 `hospital.service.require_requestable()`을 불러 확인 (false면 403 `hospital.not_requestable`). `can_request` = `is_registered_facility` + `status_verdict = normal` (해외진출법 제24조 제1항 제3호, compliance 2-1). 시연용 가상 병원(`is_demo`)은 시드를 만들 때 포함 여부를 이 줄에 추가
- 챗봇(A)도 `booking.service.list_for_patient`·`get_for_patient`를 부른다 — "내 요청 상태" 답과 제출 확인용, `modules/chatbot/bookings.py` 한 곳에서만. `booking` 모듈이 올라오기 전에는 "요청 없음"으로 동작

## 6. 요청서 입력 (`BookingCreate`, 초안)

| 칸 | 타입 | 필수 | 비고 |
|---|---|---|---|
| `department_code` | str | O | 진료과 코드 = `departments.code` (`dermatology`, `plastic`, `internal`, `ophthalmology` …) |
| `preferred_slots` | list[datetime] | O | 1~3개, 시간대 포함, 지금 이후만 → UTC로 저장 |
| `patient_timezone` | str (IANA, 예 `Asia/Taipei`) | O | 화면 표시용 |
| `lang` | str (`ko`/`en`/`zh-TW`/`zh-CN`/`vi`/`ja`) | O | 요청 언어 (`patients.preferred_lang`·프론트 번역과 같은 6개, `ja`는 2026-11-26 추가) |
| `nationality` | str (국가 코드) | O | |
| `contact_method` | str (`email`/…) | O | |
| `visa_needed` | bool | O | |
| `message` | str | X | 자유 입력 원문 → 번역은 백그라운드 |
| `health_info` | str | X | 있으면 `health` 동의 필수 |
| `consents` | list[{kind, version}] | O | `privacy` 항상 · `health_info`가 있으면 `health` · `message`나 `health_info`가 있으면 번역(해외 LLM)용 `overseas_transfer` → 빠지면 422 `consent.required` (`detail.missing`). 받은 동의는 그 요청서에 묶어 기록(`consents.booking_request_id`) |
| `residency` | `short_term` | O | 체류 형태(자기 신고). 국내 거주 외국인은 유치 대상이 아니라 요청 불가(의료법 제27조 제3항 제2호) → `short_term` 외에는 422 `validation` (2026-11-18 필수로). **제출 때 한 번 더 확인하는 값** — 판단 기준은 계정의 `residency`(6-6절, 결정 28) |
| `treatment` | str | X | 진료항목 코드 (대시보드 1-2) |

- 요청서의 `privacy` 동의 = **이 요청서 내용을 고른 병원에 전달**하는 데 대한 동의 (가입 때 `privacy`와 별개로 요청서마다). 법적 구조가 제3자 제공(개인정보보호법 제17조 제1항 제1호)인지 처리 위탁(제26조)인지는 **개인정보위 질의 8번 회신 후** 문구 확정 ([plan.md](../subject/plan.md) 11절)

### 6-1. 환자 예약 API (A, `modules/booking/router_patient.py`)

모두 **환자 로그인 필요**. 응답 `PatientBookingOut` = `BookingOut` + `replies[{text_ko, text_translated, sent_at}]`(직원이 보낸 답장만) + `reject_reason`(거절이면 2절 사유 코드, 아니면·사유 없으면 `null`). 요청서 `message`는 저장 뒤 한국어로 번역해 `message_translated`(결정 25, 실패하면 비움)

| 메서드·경로 | 하는 일 | 에러 |
|---|---|---|
| `POST /hospitals/{hospital_id}/booking-requests` | 6절 `BookingCreate` → 201, 상태 `pending`. 먼저 계정 체류 형태 확인(6-6절) | 422 `residency.required`, 403 `residency.not_eligible`, 403 `hospital.not_requestable`(`unregistered`/`not_operating`/`not_joined`), 404 `not_found`, 409 `booking.time_conflict`·`booking.same_day`·`booking.too_many`, 422 `consent.required`·`validation` |
| `GET /me/booking-requests` | 내 예약 요청 목록 (최근 순). 각 항목에 `questions[{text_original, text_translated, created_at}]` (방문 전 내 질문, 결정 32) | — |
| `POST /me/booking-requests/{id}/questions` | `{text(1~1000자)}` → 201 `PatientBookingOut`. 방문 전(`pending`·`proposed`·`confirmed`)에만, 그 요청서에 번역 동의가 있으면 병원용 한국어 번역 (결정 32) | 409 `booking.invalid_transition`, 404, 422, 429 `rate_limited`(요청서당 30개) |
| `GET /me/booking-requests/{id}` | 상세 | 404 `not_found`(남의 것 포함) |
| `POST /me/booking-requests/{id}/accept` | 병원이 제안한 시간 수락 `proposed → confirmed` | 409 `booking.invalid_transition` |
| `POST /me/booking-requests/{id}/cancel` | `{reason?}` (`CANCEL_REASONS`) → `cancelled`, `pending`·`proposed`에서만 | 409, 422 |

### 6-3. 환자 사후관리 API (A, `modules/aftercare/router_patient.py`, aftercare 주인 B — **B 확인 필요**)

모두 **환자 로그인 필요**, 내 요청서만 (남의 것은 404). 규칙은 `aftercare.service`: `patient_open()`(B가 만든 것) + 조회용 `patient_list()`·`patient_messages()`(A가 추가)

| 메서드·경로 | 하는 일 | 에러 |
|---|---|---|
| `GET /me/aftercare` | 내 대화 목록 (최근 메시지 순) `PatientThreadOut{id, request_id, status, last_message_at, last_message, unread}` — `unread` = 내가 마지막으로 보낸 뒤 병원이 보낸 수 | — |
| `GET /me/booking-requests/{id}/aftercare` | 요청서 1건의 대화 + `messages[{id, sender(patient/staff), text_original, text_translated, has_photo, created_at}]` | 404 `not_found`(대화 없음·남의 것) |
| `POST /me/booking-requests/{id}/aftercare/messages` | `{text(1~4,000자), photo?, attachments?[{path, kind(image/video), name}] (4개까지)}` → 201, 첫 메시지면 대화를 엶. 해결된 대화에 보내면 다시 `new` | 409 `booking.invalid_transition`(방문 완료 전·사후관리 미지원 병원), 404, 422 `validation`(빈 글·다른 요청서 경로의 파일) |
| `POST /me/booking-requests/{id}/aftercare/uploads` | `{name, content_type, size, thumb?}` → 201 `{path, kind, upload_url, thumb_upload_url}`. 브라우저가 `upload_url`로 파일을 `PUT`(Content-Type 그대로) 한 뒤 `path`를 `attachments`에 넣어 보냄. 사진이고 `thumb: true`면 썸네일 주소도 → 썸네일(JPEG)을 올리고 첨부에 `thumb: true` (결정 29) | 422(사진·영상 아님, 50MB 초과), 404, 409(위와 같음), 503 `storage.unavailable` |

- 사진·영상(결정 22): Supabase Storage 비공개 버킷 `aftercare-media`, 경로 `{tenant_id}/{request_id}/{무작위}.{확장자}`. 메시지 응답의 `attachments[{kind, name, url}]` — `url`은 1시간짜리 서명된 주소(못 만들면 `null`), 경로는 응답에 넣지 않음. 병원용 `GET /tenant/aftercare/{id}`도 같은 `attachments`
- 지우기(결정 23): 탈퇴(`DELETE /me`)하면 그 환자가 보낸 파일을 바로 삭제하고 메시지 `attachments`를 비움(글·`has_photo`는 남음). 나머지 고아 파일은 7-1 정기 정리가 하루 뒤
- 저장소 설정(`SUPABASE_URL`·`SUPABASE_SERVICE_ROLE_KEY`)이 없으면 업로드는 503 → 화면은 `photo: true`("사진 있음")만 보냄
- 번역(`text_translated`, 결정 25): 환자 글 → 한국어, 직원 글 → 환자 언어. 요청서 번역 동의가 있을 때만, 실패하면 `null`

### 6-2. 병원 상담 답장 API (`modules/booking/router_tenant.py`, booking 주인 B — A가 작성, **B 확인 필요**)

모두 **직원 로그인 필요**, 직원 토큰의 `tenant_id` 요청만 (다른 병원 요청은 404). 답장 저장은 `booking.service.staff_reply()`

| 메서드·경로 | 하는 일 | 에러 |
|---|---|---|
| `POST /tenant/booking-requests/{id}/replies` | `{text}`(1~2,000자, 한국어) → 201 `ReplyOut{id, text_ko, text_translated, sent_at}`. 대시보드 확인 창의 "보내기" = 직원 승인 → 바로 보낸 상태(`sent_at`), `approved_by` = 보낸 직원(직원 행이 없으면 비움). 상태는 바꾸지 않음 | 404 `not_found`, 422 `validation`(빈 글·공백만·2,000자 초과), 401 |
| `GET /tenant/booking-requests`, `GET /tenant/booking-requests/{id}` | 응답이 `TenantBookingOut` = `BookingOut` + `replies[ReplyOut]`(보낸 순)으로 바뀜 (칸 추가만, 기존 칸 그대로). 2026-11-23: `questions[{text_original, text_translated, created_at}]` 추가 (방문 전 환자 질문, 결정 32) | — |

- 번역(`text_translated`, 결정 25): 보낼 때 환자 언어로 (`ai/llm`, 요청서 번역 동의가 있을 때만, 실패하면 비움 → 환자 화면은 원문). AI 초안(`ai_draft`)은 승인 전에는 저장하지 않음 (compliance: 직원 승인 없이 발송 X)
- 환자는 6-1절 `replies`로 봄 (보낸 것만)


### 6-4. 열람 기록 (`modules/audit/`, B — A 작성 · **B 확인 필요**, 결정 24)

| 메서드·경로 | 하는 일 |
|---|---|
| `GET /tenant/audit-logs?limit=` | 자기 병원 기록 최근 순 `[{actor, action, ref, created_at}]` (limit 1~500, 기본 100) |

- 남는 행동: `booking.list`(ref `booking_requests:<건수>`) · `booking.view` · `booking.reply`(ref `booking_request:<id>`) · `aftercare.view` · `aftercare.reply`(ref `aftercare_thread:<id>`)
- 내용(글·사진)은 저장하지 않음. 다른 병원 데이터를 열려다 404가 나면 기록 없음
- 열람(`*.list`·`*.view`)은 같은 직원·같은 대상이면 1분에 1줄 (목록은 건수가 달라도 같은 열람), 답장은 매번
- 함수: `audit.service.log_action(db, tenant_id, actor, action, ref)`(5절, commit은 부르는 쪽), 조회 API용 `log_and_commit`

### 6-5. 환자 알림 API (A, `modules/notification/`, 결정 27)

모두 **환자 로그인 필요**, 자기 알림만

| 메서드·경로 | 하는 일 | 에러 |
|---|---|---|
| `GET /me/notifications` | 최근 50개 `[{id, kind(status/reply/aftercare), request_id, hospital_id, status, created_at, read}]` | — |
| `POST /me/notifications/read` | `{ids?}` (비우면 모두) → `{updated}`. 남의 id는 무시 | 422 |
| `GET /me/push/key` | `{public_key}` — VAPID 공개 키 (브라우저 `pushManager.subscribe`용, 결정 30) | 503 `push.unavailable` |
| `POST /me/push/subscriptions` | `{endpoint(https), keys{p256dh, auth}}` → 204. 같은 endpoint면 지금 환자로 옮김 | 422, 503 |
| `DELETE /me/push/subscriptions` | `{endpoint}` → 204 (내 것만) | — |
| `POST /me/notifications/realtime-token` | `{url, token, expires_at}` — Supabase Realtime 접속용 1시간 토큰 (`sub` = 환자 id, `role` = authenticated) | 503 `realtime.unavailable` |

- 기록 시점: `booking._move`(환자가 한 변경 제외) · `booking.staff_reply` · `aftercare.tenant_reply` — 모두 같은 commit
- Supabase: `notifications` RLS 정책 `notifications_own`(authenticated, `patient_id = auth.jwt()->>'sub'`), Realtime 발행 `supabase_realtime`에 추가 (마이그레이션 0010)
- 탈퇴하면 같이 삭제 (FK CASCADE)

### 6-6. 환자 체류 형태 (A, `modules/patient/`, 결정 28)

`ResidencyIn{country(ISO 2자리 거주국), alien_registration, domestic_residence, health_insurance}` — ① 외국인등록(G-1 제외) ② 국내거소신고 ③ 국민건강보험 가입자·피부양자. **하나라도 true거나 `country = KR`이면 `resident`**, 아니면 `short_term` (compliance 2-1)

| 메서드·경로 | 하는 일 | 에러 |
|---|---|---|
| `POST /auth/patient/signup` | 본문에 `residency?: ResidencyIn` 추가 (선택 — 없으면 계정 값 비움) | 422 `validation`(국가 코드 형식) |
| `PUT /me/residency` | `ResidencyIn` → `PatientOut` (다시 답하기: 가입 때 안 했거나 체류 상태가 바뀜) | 401, 422 |
| `GET /me`, `PATCH /me` | `PatientOut`에 `residency`(`short_term`/`resident`/`null`)·`residence_country` 추가 (칸 추가만) | — |

- 챗봇: 계정 값이 있으면 대화 상태보다 우선하고 `record_residency`로 바꿀 수 없음 → `resident`면 조건 맞춤 제안·예약 초안 X (중립 목록 검색은 됨)
- 저장: `patients.residency`·`residence_country`·`residency_answered_at` (마이그레이션 0011). 답만 저장, 근거 서류는 받지 않음 (자기 신고)

## 7. 챗봇 API (A, `modules/chatbot/`, 결정 16)

모두 **환자 로그인 필요**. 경로 앞 `/api/v1`. 응답 모델은 `ai/agent/schemas.py`(카드 형식의 기준) → OpenAPI

| 메서드·경로 | 하는 일 | 에러 |
|---|---|---|
| `POST /chatbot/ask` | `{session_id?, message(1~1000자), language?}` → `{session_id, text, cards[], ai_generated, blocked, medical_notice}`. `session_id`가 없으면 새 대화, `language`가 없으면 계정 선호 언어 | 404 `not_found`(남의·없는 대화), 422 `validation`, 429 `rate_limited`, 503 `chatbot.unavailable` |
| `GET /chatbot/sessions?limit=` | 내 대화 목록 `[{id, title, lang, created_at, last_message_at}]`, 최근 순, 최대 50 | — |
| `GET /chatbot/sessions/{id}` | 한 대화 + `messages[{role, content, refused, created_at}]` (개인정보를 가린 글만) | 404 `not_found` |
| `DELETE /chatbot/sessions/{id}` | 대화 삭제 → 204 | 404 `not_found` |

- **언어**: `ko`, `en`, `zh-TW`, `zh-CN`, `vi`, `ja`(2026-11-26 추가). 별칭 `zh`·`zh-Hans`→`zh-CN`, `zh-Hant`→`zh-TW`. 그 밖은 422
- **카드** `{type, data}` 9종: `hospital_list`, `hospital_suggestions`, `hospital_detail`, `price_list`, `sources`, `time_slots`, `booking_draft`, `booking_list`, `aftercare_thread`. 숫자·병원 정보는 도구 결과에서 코드가 넣음
- `aftercare_thread` 카드(결정 26): `{status: "opened", thread_id(없으면 ""), booking_id, hospital_id, topic, first_message, notice}` — 메시지는 **보내지 않음**. 화면은 버튼으로 사후관리 화면을 열고 `first_message`를 입력창에 채움, 환자가 보냄
- **요청서 카드**(`booking_draft`)의 `data.request`는 6절 `BookingCreate` 모양(희망 일시 UTC). 프론트 [제출] = `POST /hospitals/{hospital_id}/booking-requests`에 `request` + 환자가 체크한 `consents`(`data.consents_required` 목록)를 그대로. **챗봇 전용 제출 경로 없음**
- **진료과**: 챗봇은 한국어 이름을 받아 `department_code`로 바꿈. 코드 표에 없는 진료과는 병원 찾기까지만, 요청서 불가
- **저장**: 개인정보를 가린 대화 글 + 상태(체류 형태, 초안 일부, 보여 준 병원)만. 도구 결과·카드·초안의 `health_info`·`message`는 저장 X → 지난 대화를 열면 글만 보임. 30일 후 삭제, 탈퇴 즉시 삭제
- **호출 제한**: 계정당 분 10회·일 150회(가정), 계정당 대화 50개. 지금은 서버 메모리 → 운영 전 DB·캐시로

## 7-1. 내부 정리 API (A, `modules/maintenance/`)

| 메서드·경로 | 하는 일 | 에러 |
|---|---|---|
| `GET`·`POST /internal/purge` | 30일 지난 챗봇 대화 + 만료·로그아웃한 로그인 세션 + DB에 없는 하루 지난 사진·영상 파일(결정 23) 삭제 → `{chat_sessions, auth_sessions, media_files}` (지운 수, 저장소 설정 없으면 `media_files` 0) | 404 `not_found`(`CRON_SECRET` 없음 = 꺼짐), 401 `auth.required`(비밀 값 틀림) |

- 인증: `Authorization: Bearer <CRON_SECRET>` (환경변수 `CRON_SECRET`, 16자 이상). Swagger에 숨김
- **예약 작업이 하루 1번 불러야 함** (Vercel Cron 등). 부르지 않으면 30일 보관 정리가 되지 않음. Vercel Cron은 GET + 이 헤더를 자동으로 보냄 (`vercel.json` 설정은 배포 담당이)

## 8. 변경 이력

| 날짜 | 절 | 바뀐 것 | 누가 (A/B) | PR |
|---|---|---|---|---|
| 2026-11-27 | 6-2 | 병원 대시보드 그래프용 `GET /tenant/analytics/series?from&to` 신설 (최대 12구간·366일, 구간마다 `now`·`prev`의 요청·확정·방문·취소율 = 그 구간 summary의 now와 같음). 기존 `summary`는 그대로 | A가 B 파일 수정 (**사용자 지시** — B 확인 필요) | `backend-A-analytics-series` → `backend` |
| 2026-11-26 | 6·7 | 언어 코드에 `ja` 추가 (`patients`·`booking_requests`·`chat_sessions` CHECK, 마이그레이션 0014) · 챗봇 상세 `can_request_consultation` = 입점 병원만 | A·B (사용자가 둘 다 담당) | `backend-chatbot` → `backend` |
| 2026-11-25 | 3·4 | 직원 가입은 가상 병원(`is_demo`)만, 실제 병원은 403 `auth.signup_closed` (설정 `STAFF_SIGNUP_REAL_HOSPITALS`로만 엶, 결정 34) | A (**B 확인 필요**) | `backend-A-contract-signup-closed` → `backend` |
| 2026-11-24 | 2 | 병원 `proposed → confirm` 제거(제안 시간은 환자 수락만), 시간 제안은 진료시간 안만 (결정 33) | A가 B 파일 수정 (**사용자 지시** — B 확인 필요) | `backend-A-vercel-cron` → `backend` |
| 2026-11-23 | 6-3 | 사진 썸네일: 업로드 `thumb?` → `thumb_upload_url`, 첨부 `thumb?`, 응답 첨부에 `thumb_url`(환자·병원, 없으면 null) — 칸 추가만 (결정 29) | A (**B 확인 필요** — aftercare는 B 모듈, `router_tenant` 응답 칸 추가) | `backend-A-media-thumbs` → `backend` |
| 2026-11-23 | 6-1·6-2·7 | 방문 전 환자 질문 `POST /me/booking-requests/{id}/questions`, 환자·병원 예약 응답에 `questions`, 챗봇 `hospital_question` 카드(초안만) (결정 32, 마이그레이션 0013). 챗봇 조건 맞춤 제안·예약 = 입점 가상 병원만 (결정 31) | A (**B 확인 필요** — booking 응답 칸 추가, `router_tenant` 한 곳) | `backend-A-chatbot-demo-flow` → `backend` (`backend-A-web-push` 다음) |
| 2026-11-23 | 4·5·6-5 | 웹 푸시: `/me/push/key`·`/me/push/subscriptions`, 에러 `push.unavailable`, `notify()`가 commit 뒤 푸시 (모양·호출 위치 그대로, 결정 30, 마이그레이션 0012) | A (**B 확인 필요**) | `backend-A-web-push` → `backend` (`backend-A-residency` 다음) |
| 2026-11-23 | 4·6·6-1·6-6 | 환자 체류 형태 6-6 신설(가입 `residency?`, `PUT /me/residency`, `PatientOut` 칸 추가), 예약 요청 전 계정 값 확인, 에러 `residency.required`(422)·`residency.not_eligible`(403) (결정 28, 마이그레이션 0011) | A (**B 확인 필요**) | `backend-A-residency` → `backend` |
| 2026-11-20 | 6-2 | 병원 상담 답장 `POST /tenant/booking-requests/{id}/replies` 신설, 병원 목록·상세 응답에 `replies` 추가 (`TenantBookingOut`) | A (**B 확인 필요** — booking은 B 모듈) | `backend-A-booking-replies` → `backend` |
| 2026-11-17 | 4·5 | **병원 정보 공개는 등록 병원만** (결정 21): `GET /hospitals`(`ids` 포함)·챗봇 병원 찾기는 등록 병원만, 미등록 병원 상세는 404 `not_found`. `get_basic()`·`require_requestable()`(내부 호출)은 그대로 | A (**B 확인 필요**) | `backend-A-contract-registered` → `backend` |
| 2026-11-17 | 2 | 병원 직원 거절에 사유 코드(`fully_booked`/`not_offered`/`needs_consult`/`other`, 선택) | A (**B 확인 필요** — booking은 B 모듈) | `backend-A-contract-reject-reason` → `backend` |
| 2026-11-18 | 4·6 | 환자 예약 API 6-1절 신설, `hospital.not_requestable` 사유 `not_joined` 추가, `residency` 필수(`short_term`만), 동의 조건(`overseas_transfer` = 글 번역 때) 확정, `preferred_slots` 미래만 | A (**B 확인 필요**) | `backend-A-contract-booking-request` → `backend` |
| 2026-11-20 | 6-3 | 환자 사후관리 API 신설 (`/me/aftercare`, `/me/booking-requests/{id}/aftercare[/messages]`), `aftercare.service`에 `patient_list`·`patient_messages` 추가 | A (**B 확인 필요** — aftercare는 B 모듈) | `backend-A-aftercare-patient` → `backend` |
| 2026-11-20 | 4·6-3 | 사후관리 사진·영상 업로드(`…/aftercare/uploads`)·`attachments`, 에러 `storage.unavailable`(503) 추가, 병원용 메시지에도 `attachments` (결정 22, 마이그레이션 0008) | A (**B 확인 필요**) | `backend-A-aftercare-patient` → `backend` |
| 2026-11-20 | 6-3·7-1 | 탈퇴 때 사진·영상 삭제, 정기 정리 응답에 `media_files` (결정 23) | A (**B 확인 필요**) | `backend-A-aftercare-patient` → `backend` |
| 2026-11-20 | 6-1·6-2·6-3·6-4·7 | 열람 기록 API(6-4, 마이그레이션 0009), 메시지 번역(결정 25), 챗봇 `aftercare_thread` 카드에 `booking_id`·보내지 않음(결정 26) | A (**B 확인 필요**) | `backend-A-audit-translate` → `backend` |
| 2026-11-20 | 6-1·6-4 | 환자 예약 응답에 `reject_reason`, 열람 기록은 같은 직원·대상 1분에 1줄 | A (**B 확인 필요**) | `backend-A-audit-translate` → `backend` |
| 2026-11-20 | 4·5·6-5 | 알림 API 6-5 신설, `notify()` 모양 확정(commit 전 호출), 에러 `realtime.unavailable` (결정 27, 마이그레이션 0010) | A (**B 확인 필요**) | `backend-A-notifications` → `backend` |
| 2026-11-18 | 3·4 | 병원 관계자 가입·로그인 경로(`/auth/staff/signup`·`login`), 에러 `auth.hospital_taken`(409) | A (**B 확인 필요**) | `backend-A-contract-staff-auth` → `backend` |
| 2026-11-16 | 4·5 | 에러 `hospital.not_requestable`(403) 추가, `HospitalBasic` 칸 확정(`can_request` 포함), 요청서 제출 전 `require_requestable()`로 확인 | A (**B 확인 필요**) | `backend-A-contract-hospital` → `backend` |
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
