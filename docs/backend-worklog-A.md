# backend-worklog-A.md — 백엔드 A 작업 기록 (환자 쪽)

> **A만 쓰는 파일** (B는 읽기만). 세션이 끝날 때마다 **맨 위에** 항목 추가. 사람이 쓰든 AI가 쓰든 같은 형식
> B에게 부탁할 것은 "B에게 요청"에 쓰고, B는 처리하면 **B의 worklog**에 "A 요청 n 처리"라고 적음

## 형식 (복사해서 아래에 추가)

```
### YYYY-MM-DD · 브랜치 · 도구(Claude/Codex/직접)
- 한 일:
- 바뀐 계약: 없음 / contracts n절
- 테스트: 통과 n개 / 실패 내용
- 다음 할 일:
- B에게 요청:
- 막힌 것·질문:
```

## 기록

### 2026-11-11 · backend-A-chatbot · Claude
- 한 일: **7b 챗봇 API** — `origin/ai`를 이 브랜치에 merge(백엔드가 `ai.agent` 서비스 층을 import). `modules/chatbot/`에 `store.py`(`SessionStore`의 DB 구현, 환자 id로 범위 제한, 잘못된 id는 "없음"), `bookings.py`(예약 조회 게이트웨이 — `booking` 모듈이 없어 지금은 "내 요청 없음", 가짜 예약 데이터는 실제 환자에게 안 보임), `schemas.py`(`AskRequest`), `service.py`(계정의 시간대·선호 언어 채우기, `ChatServiceError` → `AppError`), `router.py`(`POST /chatbot/ask`, `DELETE /chatbot/sessions/{id}`, 모두 환자 로그인 필요). `main.py`에 라우터 등록. 응답은 `ai.agent.schemas.ChatResponse` 그대로(카드 9종이 OpenAPI에 나옴)
- 바뀐 계약: 없음. 단 **`chatbot.unavailable`(503)은 계약 4절에 아직 없음** → 7c 계약 PR에서 추가 (`/chatbot/*` 경로·카드 형식도 같이)
- 마이그레이션: 없음 (`0005` 그대로, 공용 Supabase 미적용)
- 테스트: 288개 통과 = 백엔드 98(기존 88 + 챗봇 API 10) + AI 190. 챗봇 API: 로그인 필요, 입력 검사, DB에 가린 텍스트만 저장, 다음 턴이 DB 기록·상태로 이어짐("보여 준 병원" 복원), 초안에 `health_info`·문의 내용 저장 X, **다른 환자의 대화 이어 쓰기·삭제 404**, 내 대화 삭제, 탈퇴 시 대화 삭제, 429, LLM 전부 실패 시 503·저장 안 함. 이 PC에서 `uv sync` 후 정상 실행됨(11/10의 sqlalchemy 확장 차단은 이번엔 없었음)
- 다음 할 일: 이 브랜치 → `backend` PR, 공용 DB에 `0005` 적용, 7c 계약 PR, 7d 프론트 연결
- B에게 요청: ① `booking.service.list_for_patient(db, patient_id, status)`·`get_for_patient`가 생기면 `modules/chatbot/bookings.py`만 바꾸면 챗봇의 "내 요청 상태"·제출 확인이 동작함 ② 7c 계약 PR 리뷰
- 막힌 것·질문: ① 호출 제한이 프로세스 메모리라 Vercel 여러 인스턴스에서는 따로 셈 → 운영 전 DB·캐시로 ② 이 PR에는 `ai` 브랜치 변경이 함께 들어감(`ai` → `main` PR이 먼저 머지되면 겹치는 부분은 사라짐). 병원 검색 도구는 아직 `ai`의 가상 병원 데이터를 씀 (`hospital` 모듈 생기면 교체)

### 2026-11-10 · backend-A-chatbot · Claude
- 한 일: **챗봇 대화 테이블** — `modules/chatbot/models.py`(`ChatSession`·`ChatMessage`), 마이그레이션 `0005`(`chat_sessions`·`chat_messages`, RLS 켬), `sessions.py`(`delete_all`·`purge_older_than`), `auth.service.withdraw`가 챗봇 대화도 즉시 삭제, `core/db_models.py` 등록. 결정 16 기록, db-schema 5절·backend-plan 로그인 표 갱신
- 바뀐 계약: 없음 (`/chatbot/*` 계약은 7c에서 별도 PR). 단 **이전 결정 3 일부 변경(챗봇 로그인 필요)** — 결정 16
- 마이그레이션: 있음 `0005`. **공용 Supabase에는 아직 적용하지 않음**(PR 머지 뒤 `alembic upgrade head`)
- 테스트: 88개 통과 (기존 78 + 챗봇 테이블 10). `alembic upgrade head`(0001~0005, 임시 SQLite)·`alembic check`(모델과 일치)·`downgrade 0004`→`upgrade head`·PostgreSQL SQL 출력(JSONB, identity, ON DELETE CASCADE, RLS) 확인. 탈퇴 삭제 연결을 빼면 테스트가 실패하는 것도 확인
- 다음 할 일: `SessionStore` 인터페이스(`ai/agent/session_store.py`)의 DB 구현 + `POST /chatbot/ask` 라우터(`ai` 브랜치가 `main`에 들어온 뒤 — 지금 `backend`에는 `ai/` 패키지가 없음), 계약 PR
- B에게 요청: 결정 16(챗봇 로그인 필요, 요청서는 같은 API로 제출) 확인. 병원 쪽 `booking.service.create_request`·`list_for_patient`가 오면 챗봇이 제출 확인에 씀
- 막힌 것·질문: ① 증상을 쓰면 건강정보가 계정에 저장되어 AGENTS.md 6절과 충돌(스키마 5절 ⚠️) — 고지·마스킹·30일·삭제 버튼으로 진행하되 **팀 확인 필요**, 개인정보보호위원회 질의 8번 회신 전. 요청서 초안의 `health_info`는 저장 상태에서 빼는 것이 안전(7a 서비스 층에 반영 예정) ② 이 PC는 보안 정책이 `sqlalchemy`의 컴파일된 확장 파일을 막아, 일회용 가상환경에서 그 파일만 지우고 순수 파이썬으로 테스트함(팀 환경·`uv.lock` 무관, 속도만 느림)

### 2026-11-05 (3) · backend-A-account · Claude
- 한 일: **Supabase DB 초기화** — `alembic downgrade base` → `upgrade head`로 `0001`~`0004` 다시 적용 (현재 `0004`, 모든 테이블 비어 있음, RLS 켜짐). 기존 테스트 계정 3개·세션·동의 삭제. 아래 항목의 "Supabase 미적용"은 이걸로 처리
- 바뀐 계약: 없음
- 테스트: 78개 통과 (변경 없음). 테이블 목록·행 수·RLS 확인
- 다음 할 일: 찜·방문 기록 API
- B에게 요청: 공용 Supabase에는 `@example.com` 가짜 계정만 (실제 메일 X). DB가 비었으니 테스트 계정은 새로 가입
- 막힌 것·질문: 없음

### 2026-11-05 (2) · backend-A-account · Claude
- 한 일: **탈퇴 = 즉시 삭제** (결정 15). `DELETE /me` → 비밀번호 확인 → 세션 전부·`patients` 행 삭제, 동의 기록은 남기고 `patient_id`만 비움(`consent.detach_patient`). `deleted_at` 칸·부분 UNIQUE 제거 → 이메일 일반 UNIQUE, `patient.get_live*` → `get`·`get_by_email`. 마이그레이션 `0004`(예전 탈퇴 표시 행 정리 후 칸 삭제) — **Supabase 미적용** (`0003`과 같이)
- 바뀐 계약: 없음 (응답 그대로, 변경 이력에 한 줄)
- 테스트: 78개 통과 (탈퇴: 내 행·세션 삭제, 다른 환자 그대로, 동의 4개 중 내 것 2개 `patient_id` 비움, 바로 재가입). SQLite로 `0004` 올리기·내리기·다시 올리기 확인
- 다음 할 일: Supabase에 `0003`·`0004` 적용, 찜·방문 기록 API
- B에게 요청: 11/4 요청 중 "정기 삭제에 탈퇴 계정 파기"는 **취소** (탈퇴 즉시 삭제). 정기 삭제는 만료 세션(`sessions.purge_dead(db)`)·알림 90일 등만
- 막힌 것·질문: 없음

### 2026-11-05 · backend-A-account · Claude
- 한 일: `auth_sessions`가 계속 쌓이지 않게 `sessions.purge_dead()` 추가 — 만료됐거나 로그아웃한 세션 행 삭제. 로그인·가입할 때 그 환자 것만 정리, `patient_id` 없이 부르면 전체 (배포 후 cron용)
- 바뀐 계약: 없음
- 테스트: 79개 통과 (정리 2개 추가: 내 것만 지움·다른 환자 그대로·살아 있는 세션 유지)
- 다음 할 일: Supabase에 `0003` 적용, 찜·방문 기록 API
- B에게 요청: 배포 때 Vercel cron은 **하나로** (무료 플랜 하루 1번) — 그 안에서 환율 미리 받기 + `sessions.purge_dead(db)` 전체 정리를 같이
- 막힌 것·질문: 탈퇴 계정 행을 실제로 지우는 시점(보관 기간) 미정

### 2026-11-04 (2) · backend-A-account · Claude
- 한 일:
  - `DELETE /me` 탈퇴: 비밀번호 확인 → `deleted_at` + 모든 기기 로그아웃(`revoke_all`). 동의 기록은 남김, 같은 메일 재가입 가능. 실제 삭제(파기)는 정기 삭제 스크립트(B)
  - `modules/fx`: 환율 `GET /exchange-rates` — **한국은행 ECOS 731Y001**(주요국통화의 대원화환율, 일별)에서 USD·CNY·TWD·VND(100동당) → 1원당 외화로 저장. **매일 오전 10시(KST) 기준 "적용일"**(10시 전이면 어제)로 하루 1번만 받고, 다음 날 10시 전까지 같은 값으로 안내. 주말·공휴일은 직전 영업일 값. 실패하면 저장값(`stale`), 없으면 503 `fx.unavailable`. 키는 `.env` `ECOS_API_KEY`, 시각은 `FX_SWITCH_HOUR_KST`(기본 10)
  - 마이그레이션 `0003` `exchange_rates`(currency·rate·base_date·applied_on·fetched_at, +RLS) — **Supabase 미적용**
  - 프론트(`frontend-mypage-currency`): 마이페이지 "내 계정"을 탈퇴하기로(프로필·언어 설정 문구 제거, 비밀번호 확인 창), 가격 가이드 통화별 참고 환산(원화 같이 표시, 출처·기준 시각)
- 바뀐 계약: contracts 1절(`fx/` 주인 A)·4절(`fx.unavailable`)
- 테스트: 77개 통과 (탈퇴 3, 환율 16: 10시 전후·적용일 하루 1번·주말·VND 100동·실패). 임시 SQLite로 화면 확인 (탈퇴·틀린 비밀번호·데모 비활성, USD·VND·TWD·CNY × 언어)
- 다음 할 일: Supabase에 `0003` 적용, 찜·방문 기록 API
- B에게 요청: 정기 삭제 스크립트에 "탈퇴 계정 파기" 포함 / 배포 시 Vercel cron `0 1 * * *`(UTC 01:00 = KST 10:00)으로 `GET /api/v1/exchange-rates` 미리 호출(선택, 무료 플랜 ±59분), Vercel 환경변수에 `ECOS_API_KEY`
- 막힌 것·질문: ECOS에 당일 값이 몇 시에 들어오는지 미확인 (11/4 값은 오후 조회 시 있음) → 10시에 당일 값이 없으면 전 영업일 값, 화면에 기준일 표시

### 2026-11-04 · backend-A-auth · Claude
- 한 일:
  - DB: Docker 대신 Supabase + Vercel (결정 12). `core/db.py`(SQLAlchemy 2 동기 + psycopg 3, NullPool, prepared statement 끔, UTC 강제 `UTCDateTime`), `core/db_models.py`(모델 등록), `.env.example`에 `DATABASE_URL`
  - 마이그레이션은 A가 (결정 13). `backend/alembic.ini`(Windows cp949 때문에 ASCII만), `env.py`, 리비전 `0001` = `patients`·`auth_sessions`·`consents` + RLS(Supabase 공개 API 차단)
  - 로그인 방식: 이메일 인증코드 → **이메일 + 비밀번호 회원가입** (결정 11). `POST /auth/patient/signup`(201, 14세 확인 + `terms`·`privacy` 필수, 바로 토큰), `POST /auth/patient/login`(실패는 `auth.invalid_credentials` 하나, 없는 이메일도 해시 검증 시간 똑같이)
  - 로그아웃 즉시 무효 (결정 14): `auth_sessions` 테이블, 토큰에 `sid`, `current_patient()`가 요청마다 세션 확인, `POST /auth/patient/logout`(204, 이 기기만), `sessions.revoke_all()`(탈퇴·비밀번호 변경용)
  - `modules/patient`: `GET /me`, `PATCH /me`(언어·시간대·표시 이름만. 이메일·비밀번호는 못 바꿈). `modules/consent`: `record()`·`require()`
  - 프론트 연결: CORS(`CORS_ORIGINS`, 기본 localhost 5403·5173, 쿠키 X), 가입 시 `display_name`(선택) 받음, `/` → `/docs`. 프론트 회원가입·로그인 폼은 `frontend-auth` 브랜치 (프론트 담당 리뷰 필요)
  - `core/errors.py`: FastAPI 입력 오류도 `{code: "validation"}` 형식, `core/config.py`: `.env`를 파일 위치 기준으로 (PR #3 리뷰 의견)
- 바뀐 계약: contracts 1절(alembic 주인 A), 3절(환자 토큰 `sid`, 세션 확인), 4절(`validation` 형식, `auth.code_invalid` 삭제, `auth.invalid_credentials`·`auth.email_taken` 추가) — **B 확인 필요**
- 테스트: 58개 통과 (CORS·표시 이름·DB 주소 정규화 포함. 로그아웃 즉시 401·다른 기기 유지·전체 로그아웃·남의 세션 X 포함. 새 36개: 가입·해시 저장·이메일 정규화·중복·14세·필수 동의·입력 오류·로그인 실패 같은 응답·탈퇴 후 로그인 X·재가입·/me 권한·동의 require). 마이그레이션 = 모델 비교 차이 0, upgrade/downgrade 확인 (SQLite)
- Supabase: 연결 확인(PostgreSQL 17, 싱가포르 `ap-southeast-1`, 트랜잭션 풀러) → `0001`·`0002`(alembic_version RLS) 적용, 테이블 4개 RLS 켜짐·정책 0. 실제 DB로 가입·중복·로그아웃 즉시 401·재로그인 확인 후 테스트 계정 삭제. 한국 PC→싱가포르라 `/me` 약 0.7초 → Vercel은 `sin1`에 배포할 것
- 다음 할 일: Vercel 진입점(`sin1`). pgvector는 챗봇 때 마이그레이션으로 켜기. 요청서 환자 router(B `booking.service` 필요)
- B에게 요청:
  1. 결정 11~14, contracts 1·3·4절 변경 확인 (Docker 안 씀, 마이그레이션 A, 비밀번호 로그인)
  2. `staff_users`·`booking_requests` 모델 만들면 알려주기 → A가 마이그레이션 + `consents.booking_request_id` FK 추가
- 막힌 것·질문: 로그인 시도 제한·비밀번호 재설정(메일 필요)은 아직 없음. 비밀번호 규칙(8~128자)은 팀 확인

### 2026-11-03 · backend-A-auth · Claude
- 한 일: 전체 DB 스키마 초안 v3 [backend-db-schema.md](backend-db-schema.md) — 마이페이지(찜·방문 기록(리뷰 X)·여행 여러 개·일정 항목·알림함, 조회 기록·체크리스트 체크 상태는 브라우저 localStorage만), 챗봇 대화(로그인 시만), `patients.display_name`, `price_stats.scope` 추가. 프론트 마이페이지 코드(`origin/frontend` f8da9c6)에 맞춤
- 바뀐 계약: 없음 (제안 단계. 확정되면 contracts 1절 주인에 새 모듈 `favorite/trip/chatbot` 추가 PR)
- 테스트: 없음 (문서만)
- 다음 할 일: B 검토 후 `models.py` 작성, 마이페이지 API
- B에게 요청:
  1. 스키마 6절 `booking_requests.id`를 uuid로 (알림 FK)
  2. 확정되면 마이그레이션 생성
- 막힌 것·질문: 챗봇 대화 저장이 "환자 계정에 건강정보 저장 X"와 부딪힐 수 있음 → 팀 확인 (스키마 5절)

### 2026-10-30 · backend-A-auth · Claude
- 한 일:
  - 파이썬 환경: 루트 `pyproject.toml`(uv), `.python-version` = 3.12, `uv.lock`
  - `core/config.py`(설정, JWT 비밀 키 32자 미만이면 시작 실패), `core/errors.py`(`AppError` + `{code, message, detail}` 핸들러), `core/security.py`(JWT 발급·검증, `current_patient()`·`current_staff()`)
  - `main.py` + `GET /api/v1/health`
  - `.env.example`에 `JWT_*` 항목 추가 (실제 키는 각자 `.env`)
- 바뀐 계약: 없음 (contracts 3절 토큰·4절 에러 코드 `auth.required`·`auth.forbidden` 그대로 구현)
- 테스트: 13개 통과 (`uv run pytest`) — 토큰 왕복, 만료·잘못된 키·모르는 role → 401, 역할 다름 → 403, 직원 토큰 tenant_id 필수, health
- 다음 할 일: 환자 인증코드 로그인(`/auth/patient/code`·`verify`) — DB 필요
- B에게 요청:
  1. `core/` 공통 파일(config·errors·main) 초안 확인 → `db.py` 추가할 때 같은 `Settings`에 DB 설정 넣기
  2. `docker-compose.yml` + `core/db.py` + 첫 마이그레이션 (A의 `patients`·`login_codes`·`consents` 모델이 그 위에 올라감)
- 막힌 것·질문: 이 PC는 uv가 Python 3.15를 고르다 설치 오류 → 3.12로 고정. 팀원도 `uv sync` 한 번이면 같은 환경

### 2026-10-30 · backend · —
- 한 일: worklog 파일 생성 (아직 코드 작업 없음)
- 다음 할 일: contracts 초안 같이 확정, `auth` 틀(JWT 발급·검증)
- B에게 요청: 없음
