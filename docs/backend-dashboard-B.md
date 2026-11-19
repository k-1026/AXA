# backend-dashboard-B.md — 병원 대시보드 백엔드 진행 계획 (B)

> 작성 2026-11-16 · 브랜치 `backend-B-dashboard` (`backend` 최신에서 생성)
> 기준: `docs-dashboard-integration` 브랜치 [docs/dashboard-integration.md](dashboard-integration.md) (11/12 초안), [backend-contracts.md](backend-contracts.md), [backend-decisions.md](backend-decisions.md)

## 0. 지금 상태 (2026-11-16, `origin/backend` 기준)

| 있음 | 없음 (대시보드에 필요) |
|---|---|
| 환자 가입·로그인·탈퇴, 동의, 환율, 챗봇 API·대화 세션 (리비전 0001~0005) | **`booking_requests`·`booking_events`·`replies`** (B) |
| `core/security.py`의 `StaffPrincipal`·직원 토큰 형식 | **`tenants`·`staff_users`** (B), **직원 로그인 `POST /auth/staff/login`** (A) |
| `chatbot/bookings.py` — B의 `booking.service`가 생기면 연결하도록 비워 둠 | `availability`, 병원용 API 전부 |

→ 명세의 **1단계 "예약 지표"는 booking·tenant가 먼저 있어야** 계산 가능. 그래서 0단계(기반)를 앞에 둠

## 1. 진행 순서 (추천)

| 단계 | 할 일 | 주인 | 완료 기준 | PR |
|---|---|---|---|---|
| **0-a 기반 모델** | `tenants`(등록번호·플랜·요청 기능 on/off), `staff_users`, `booking_requests`(+ 명세 2-2 칸 `channel`·`treatment`·`topic_tags` 처음부터 포함), `booking_events`(+ `reason`), `replies` 모델 | B 모델 → **A가 마이그레이션 생성** (결정 13) | 모델 PR + A에게 리비전 요청 | PR 1 |
| **0-b 상태 흐름** | `booking.service`: `create_request`, `list_for_patient`, `get_for_patient`, `patient_accept`, `patient_cancel(reason)`, 병원 `confirm`·`reject`·`propose`, **`visited`·`no_show`** (명세 2-3). 흐름 밖 변경 → 409 `booking.invalid_transition`, 모든 변경 `booking_events` 1건 | B | 상태 전이 테스트 통과 | PR 2 |
| **0-c 병원용 API** | `GET /tenant/booking-requests`, 상세, `confirm`·`reject`·`propose`, `POST …/visited`·`/no-show`. 전부 `current_staff().tenant_id`로만 | B (직원 로그인은 A) | 병원 A 직원이 병원 B 요청 조회 → 404 | PR 3 |
| **1 예약 지표** | `GET /tenant/analytics/summary`·`/booking` — `sample.ts`의 `KPI`·`TODAY`·`FUNNEL`·`FIRST_REPLY`·`CANCEL_REASONS`·`REPEAT_CHANGES`·`PREFERRED_DAYS`와 **칸 이름·모양 동일**. 소표본은 서버에서 `null` + `suppressed` | B | 시드 데이터로 홈 KPI·단계별 전환이 실제 계산값 | PR 4 |
| 2 병원 설정 | `tenant_settings`, `settings_history`, `GET·PUT /tenant/settings`, `GET /tenant/setup-status`, `availability` | B (+A 리비전) | 병원이 FAQ 입력 → 환자 상세에 보임 | PR 5 |
| 3 유입 기록 | `page_events`, `promo_links`, `POST /events`(로그인 X, 요청 제한), `/tenant/analytics/inflow` | `POST /events`는 환자 쪽 → **A와 담당 정하기** | 홍보 링크 방문이 경로별 표에 집계 | PR 6 |
| 4 사후관리 | `aftercare_threads`, `satisfaction`, `/tenant/aftercare`, `/tenant/analytics/aftercare` | B (+ 6절 결정 후) | 사후관리 탭 처리 현황이 실제 값 | PR 7 |

- PR은 단계마다 1개, 마이그레이션은 A에게 하루 1~2개로 모아서 요청
- `chatbot/bookings.py`는 0-b가 끝나면 A(또는 AI 담당)에게 연결 요청 (그 파일은 A 주인)

## 2. 시작 전에 정할 것 (B가 결정하거나 확인)

| # | 항목 | 추천 | 누구와 |
|---|---|---|---|
| 1 | `visited`·`no_show` 상태 추가 (명세 2-3, "백엔드 B 확인 필요") | **추가** — contracts 2절·decisions에 기록 | B 결정 → A 확인 |
| 2 | 환자가 `proposed`를 거절하면? (contracts 2절 "미정") | `cancelled`로 (사유 `schedule`) | B 결정 |
| 3 | 상담 방식·사후관리 저장 (명세 6절) | 저장은 요청서에 딸린 메시지(`replies`), `aftercare_threads`는 상태·태그만 | 팀 |
| 4 | 직원 로그인 일정 | 0-c 전까지 필요 — 없으면 테스트는 토큰 직접 발급(`create_access_token(role="staff")`)으로 | A |
| 5 | `POST /events` 담당 | 환자 쪽 공개 API라 A, 테이블·집계는 B | A |
| 6 | 소표본 기준 5명·30회·3건 | 명세대로 시작 | 팀 |

## 3. A에게 요청할 것 (worklog B "A에게 요청"에 옮겨 적기)

1. 0-a 모델 PR 리뷰 후 **마이그레이션 리비전 생성** (결정 13)
2. 직원 로그인 `POST /auth/staff/login` (+ `staff_users` 비밀번호 해시 방식 맞추기)
3. `db_models.py`에 `booking`·`tenant` 모델 import 한 줄 (A·B 공동 파일)
4. `POST /events` 담당 여부

## 4. 지킬 것

- 병원 API는 전부 `current_staff()`의 `tenant_id`로만, 다른 병원 숫자는 어떤 형태로도 X
- 통계 값은 코드(`key`·`unit`)만, 화면 글자는 프론트
- 소표본 숨김은 **서버에서**
- `page_events`에 patient_id·IP·기기 정보 저장 X
- 만족도는 환자 화면에 공개 X
- 가상 데이터만, `.env` 커밋 X

## 5. 메모

- `backend-B-health-404` 브랜치(health DB 확인, 404·405 형식, 결정 18)는 아직 `backend`에 안 합쳐짐 → 그 PR을 먼저 합치고 이 브랜치에 `backend`를 다시 받으면 충돌이 적음
- 명세 원문은 아직 `docs-dashboard-integration` 브랜치에만 있음 → 그 PR이 합쳐지면 이 문서의 링크가 살아남
