# backend-plan.md — 백엔드 기획 (초안 v2)

> 작성 2026-10-30 · v2 수정 2026-10-30 (PostgreSQL 바로 사용, 환자 계정 도입, 조문·데이터 수치 재확인)
> 근거: [plan.md](../subject/plan.md) 3·4·5·7·8절, [compliance.md](compliance.md), [agent-spec.md](agent-spec.md), [폴더구조-v2-검토.md](../research/기술/폴더구조-v2-검토.md), [다국어-번역-범위.md](../research/기술/다국어-번역-범위.md)
> 상태: **제안**. 팀 결정 = FastAPI, PostgreSQL, 요청서 제출만 환자 계정 필요. 나머지는 팀 검토

## 0. 한 줄 요약

백엔드가 하는 일 3가지:
1. 공공 병원 정보를 **로그인 없이, 읽기 전용**으로 제공
2. **로그인한 환자**의 예약·상담 요청서를 받아 상태 관리 (`대기 → 확정·거절·시간 제안`)
3. AI 기능(번역·요약·답장 초안·챗봇)을 **기록·직원 승인 절차**와 함께 호출

## 1. 결정 사항 (v2)

| 항목 | 결정 | 이유 | 준비할 것 |
|---|---|---|---|
| DB | **PostgreSQL 처음부터** | SQLite→PostgreSQL 이전 작업 없음, 시간대·JSON·동시 접속 차이 미리 해결, 챗봇 벡터 검색을 **pgvector**로 같은 DB에서 | 팀원 모두 같은 DB를 띄우도록 **Docker Compose** (`pgvector/pgvector` 이미지, `CREATE EXTENSION vector;`) [T1]. Docker를 못 쓰는 팀원은 공용 호스팅 DB (가상 데이터만) |
| 환자 계정 | **열람은 로그인 X, 요청서 제출·내 요청 보기만 로그인** | 열람 = 공공정보 제공 성격 유지. 요청은 계정으로 → 상태 확인·남용 방지·동의 기록 | 아래 6절 "환자 계정" 조건 |

## 2. 지금 폴더 구조 점검

현재 `backend/src/modules/`에는 `hospital/ price/ auth/ booking/ tenant/ subscription/ agent/`가 **빈 폴더**(`.gitkeep`만)로 있음.

### 2-1. 빠진 것 (추가 필요)

| 빠진 것 | 왜 필요한가 | 제안 위치 |
|---|---|---|
| **앱 진입점·공통 설정** | FastAPI 앱, DB 연결, 환경변수, CORS(앱 2개), 에러 형식 | `backend/src/main.py`, `backend/src/core/` |
| **DB 테이블 정의·마이그레이션** | 테이블을 바꿀 때 팀원 DB가 같이 바뀌어야 함 | `modules/*/models.py` + `backend/alembic/` |
| **로컬 DB 실행 파일** | PostgreSQL 설치 방법 통일 | 루트 `docker-compose.yml` |
| **환자 계정** | 요청서 제출을 로그인 사용자만 | `modules/patient/` |
| **동의(consent)** | 개인정보·건강정보 동의를 **구분해서** 받고 기록 (개인정보보호법 제22조 제1항, 제23조 제1항 제1호) → 나중에 증명 | `modules/consent/` |
| **기록(audit)** | 화면(`web-hospital/automation-log`)은 있는데 저장하는 백엔드가 없음. "직원 승인 후 발송" 증명 | `modules/audit/` |
| **알림(notification)** | 확정·거절·제안 시 환자에게 알림 + 로그인 인증코드 메일 | `modules/notification/` |
| **챗봇 API** | `ai/chatbot`은 있는데 웹에서 부를 엔드포인트가 없음 | `modules/chatbot/` (얇은 래퍼) |
| **가용 시간(availability)** | `ai/agent/tools/schedule.py`가 시간을 제안하려면 병원 예약 가능 시간 데이터 필요 | `modules/booking/` 안 |
| **데이터 적재 스크립트** | `data/` 병원 데이터 → DB, 가상 데모 데이터 넣기 | `backend/scripts/load_hospitals.py`, `seed_demo.py` |
| **OpenAPI 내보내기** | `packages/shared-types`를 자동 생성하려면 스키마 파일을 뽑는 단계 필요 (openapi-typescript는 OpenAPI 3.0·3.1 지원) [T3] | `backend/scripts/export_openapi.py` |
| **테스트** | 규제 규칙(정렬, 상태 권한, 동의 필수, 병원별 격리)이 깨지지 않는지 자동 확인 | `backend/tests/` |

### 2-2. 이름·역할 정리가 필요한 것

| 폴더 | 문제 | 제안 |
|---|---|---|
| `modules/agent/` vs `ai/agent/` | 둘 다 "agent" → 역할 혼동 | `ai/agent` = 도구·프롬프트(로직), `backend/modules/agent` = **API + 승인·기록**만 |
| `modules/auth/` vs `patient/` vs `tenant/` | 로그인 주체가 2종류(환자·병원 직원) | `auth` = **로그인 공통**(환자 인증코드, 직원 비밀번호, 토큰 발급), `patient` = 환자 프로필, `tenant` = 병원 계정·직원·격리 |
| `modules/price/` | 병원별 가격이 아니라 **지역 통계**만 ([가격-표시-방식.md](../research/의료관광/가격-표시-방식.md)) | 이름 유지, 테이블은 `price_stats`(미리 계산) |
| `backend` ↔ `ai` 연결 | 백엔드가 `ai/` 코드를 어떻게 부르는지 안 정함 | **같은 Python 프로세스에서 import** (데모 규모엔 별도 서버 불필요). 루트에 `pyproject.toml` 하나 |

### 2-3. 모듈 안 파일 규칙 (모든 모듈 공통)

```
modules/booking/
├── router.py       # URL·HTTP (APIRouter → main.py에서 include_router) [T4]
├── schemas.py      # 요청·응답 모양 (Pydantic) → OpenAPI → TS 타입
├── models.py       # DB 테이블 (SQLAlchemy)
├── service.py      # 규칙 (상태 변경 가능 여부, 권한, 동의 확인)
└── repository.py   # DB 읽기·쓰기 (선택, 작으면 service에 합침)
```
- **규제 규칙은 `service.py`에** → 테스트가 쉬움 (예: "환자 쪽은 `confirmed`로 못 바꿈")

## 3. 제안 구조 (v2)

```
docker-compose.yml          # PostgreSQL + pgvector       ← 추가
backend/
├── alembic/                # DB 마이그레이션
├── scripts/
│   ├── load_hospitals.py   # data → DB
│   ├── seed_demo.py        # 가상 병원 3곳·가상 환자·가상 요청
│   └── export_openapi.py   # → packages/shared-types
├── src/
│   ├── main.py
│   ├── core/               # config.py db.py security.py errors.py
│   └── modules/
│       ├── hospital/       # 공공 병원 정보 (읽기 전용) + 검색·필터
│       ├── price/          # 지역 가격 통계 (읽기 전용)
│       ├── auth/           # 로그인 공통: 환자 인증코드, 직원 비밀번호, 토큰
│       ├── patient/        # 환자 계정 (최소 정보)       ← 추가
│       ├── booking/        # 요청서·상태·답장·가용 시간
│       ├── consent/        # 동의 기록                   ← 추가
│       ├── notification/   # 메일 (데모는 콘솔 출력)     ← 추가
│       ├── tenant/         # 병원 계정·직원·데이터 격리
│       ├── subscription/   # 플랜·좌석·AI 사용량 (목업)
│       ├── agent/          # AI 도구 호출 API + 승인
│       ├── chatbot/        # 챗봇 API                    ← 추가
│       └── audit/          # 자동화·승인 기록             ← 추가
└── tests/
```

## 4. 데이터 모델 (초안)

### 4-1. 공공 정보 (읽기 전용, 적재 스크립트로 채움)

| 테이블 | 주요 칸 | 원천·규모 (2026-10-28 수집분, 직접 집계) |
|---|---|---|
| `hospitals` | id, ykiho, 이름(한글·로마자), 종별, 시군구, 주소(한글·영문), 전화, 위도·경도, 홈페이지, 등록 유치기관 여부, 인증 여부, `is_demo`, 출처, 수집일 | `daegu_hospitals.csv` **4,242행**(ykiho 중복 없음), 시군구 9개(군위군 포함), 종별 13개. 시연은 `is_demo=true` 가상 병원 |
| `hospital_departments` | hospital_id, 진료과 코드 | 필터용 |
| `hospital_hours` | hospital_id, 요일, 시작·끝(`HH:MM`로 정규화), 점심, 메모(한글 원문), 휴진 상태(`closed/open/emergency_only/unknown`), 출처, 확인일 | `daegu_hospital_hours.csv` 4,242행 중 상세 정보 있는 곳 1,212곳. 메모는 번역 안 하고 원문 |
| `nonpay_items` | 코드, 한글명, 영어·번체·베트남어명, 검수 여부 | `nonpay_item_codes.csv` 943개 중 대구 가격 데이터에 쓰인 **607개**만 먼저 번역 |
| `price_stats` | 항목 코드, 지역, 기관 수, 중앙값, 사분위, 기준일 | `daegu_nonpay_prices.csv`(병원 224곳)에서 **미리 계산**. 기관 5곳 미만은 저장 안 함 → 대구 전체 기준 607개 중 **402개** 항목이 5곳 이상 |

### 4-2. 서비스 데이터 (개인정보 포함 → 보호 필요)

| 테이블 | 주요 칸 | 규칙 |
|---|---|---|
| `patients` | id, 이메일(인증됨), 선호 언어, 시간대, 만 14세 이상 확인, 가입·탈퇴 시각 | **최소 정보만** (제16조 제1항). 이름·국적·건강정보는 계정에 안 둠 |
| `login_codes` | 이메일, 인증코드 해시, 만료 시각, 시도 횟수 | 코드 원문 저장 X, 짧은 만료·시도 제한 |
| `tenants` | id, hospital_id, 등록번호, 플랜, 요청 기능 on/off | 요청 기능은 **등록 유치의료기관만** on |
| `staff_users` | id, tenant_id, 이메일, 비밀번호 해시, 역할(`owner/staff`) | 다른 tenant 데이터 조회 불가 |
| `booking_requests` | id, **patient_id**, hospital_id, 상태, 요청 언어, 국적, 연락 방법, 희망 날짜 후보(여러 개, UTC), 진료과, 비자 필요 여부, 자유 입력(원문·번역), 건강정보(선택), 환자 시간대, 생성 시각 | 상태 기본값 `pending`. 국적·연락처는 **요청서 단위**로 받음 |
| `booking_events` | request_id, 이전→다음 상태, 행위자(환자 id / 직원 id), 제안 시간, 시각 | **상태 이력** (지우지 않음) |
| `replies` | request_id, 종류(템플릿/자유), 한국어 원문, 번역문, AI 초안 여부, 승인 직원, 발송 시각 | 승인 없으면 환자에게 안 보임 |
| `consents` | patient_id, request_id(있으면), 종류(`terms/privacy/health/overseas_transfer`), 문구 버전, 언어, 동의 시각, 철회 시각 | 건강정보 칸이 있으면 `health` 동의 필수 |
| `availability` | tenant_id, 요일·시간대 or 날짜별 슬롯 | `schedule.py` 입력 |
| `audit_logs` | tenant_id, 행위(도구 호출·발송·상태 변경), 입력·출력 참조, 승인자, 시각 | automation-log 화면 |
| `llm_usage` | tenant_id(또는 `platform`), 서비스(챗봇/에이전트), 토큰, 시각 | 구독 "AI 사용량" 기준 |
| `chatbot_chunks` | 문서 id, 출처 URL, 기준일, 본문, 임베딩(`vector`) | pgvector. 공공 문서만 |

## 5. 예약 요청 상태 흐름

```
             (병원) 확정
 pending ─────────────────▶ confirmed
   │  │     (병원) 거절
   │  └──────────────────▶ rejected
   │   (병원) 다른 시간 제안
   └──────▶ proposed ──(환자) 수락──▶ confirmed
                └──────(환자) 거절──▶ ? (팀 결정)
 (환자) 취소: pending·proposed → cancelled
 (시간 경과) 희망 날짜가 모두 지남 → expired
```

| 규칙 | 근거 |
|---|---|
| `confirmed`·`rejected`·`proposed`로 바꾸는 건 **병원 직원 계정만** | compliance.md "확정은 병원" |
| `proposed → confirmed`(환자 수락)는 병원이 먼저 제시한 시간 → 병원 결정으로 봄 | 팀 확인 필요 |
| 환자는 **자기 요청만** 조회·수락·취소 | 계정 도입으로 조회 토큰 대신 `patient_id` 확인 |
| 모든 변경은 `booking_events`에 남김 | 질의 회신·분쟁 대비 |

## 6. 환자 계정 (v2 추가)

| 항목 | 설계 | 근거 |
|---|---|---|
| 로그인 방식 | **이메일 인증코드(OTP)**, 비밀번호 없음 → 비밀번호 저장·재설정 기능 불필요. 데모는 메일 대신 **콘솔 출력** | 해외 환자 가입 부담 ↓ |
| 소셜 로그인 (Google·LINE 등) | 확장 단계 | MVP 범위 축소 |
| 저장 정보 | 이메일·선호 언어·시간대만. 건강정보는 **요청서에만** | 최소 수집, 입증 책임은 처리자 (제16조 제1항) |
| 만 14세 미만 | 가입 시 "만 14세 이상" 확인, 미만은 MVP에서 가입 불가 | 14세 미만은 법정대리인 동의·확인 필요 (제22조의2 제1항) |
| 동의 | 가입 시 이용약관·개인정보, 요청서 제출 시 건강정보(선택 칸 쓸 때)·국외 이전(해외 LLM 쓸 때)을 **각각 구분** | 제22조 제1항, 제23조 제1항 제1호, 제28조의8 제1항 제1호 |
| 1:1 상담 창구화 방지 | 메시지는 **요청서 단위**로만(답장·제안), 자유 채팅 X | plan.md 7절 (`consultation/`은 확장 단계) |
| 탈퇴·파기 | 탈퇴 API + 요청서 보관 기간 지나면 삭제·익명화 스크립트 (기간은 질의 회신 후) | 불필요해지면 지체 없이 파기 (제21조 제1항) |
| 남용 방지 | 계정당·IP당 제출 횟수 제한, 같은 병원 미처리 요청 중복 금지, 인증코드 시도 제한 | — |

## 7. API 목록 (초안, 모든 경로 앞에 `/api/v1`)

### 환자용 (`apps/web-platform`)

| 메서드·경로 | 로그인 | 하는 일 | 주의 |
|---|---|---|---|
| `GET /hospitals` | X | 검색·필터(지역·진료과·요일·시간·휴진·등록·요청 가능), 정렬(`distance`·`name`만) | 구독 여부로 정렬 X |
| `GET /hospitals/{id}` | X | 상세 + 진료시간 + 출처·수집일 + 전화·이메일 | 다른 연락 경로 항상 포함 |
| `GET /prices/stats?item=&region=` | X | 지역 통계 | 5곳 미만 없음 |
| `POST /chatbot/ask` | X | 챗봇 질문 | 출처·기준일 포함, 의료 판단 거절. 요청 횟수 제한 |
| `POST /auth/patient/code` · `/auth/patient/verify` | X | 인증코드 발송·확인 → 토큰 | 시도 제한 |
| `GET·PATCH·DELETE /me` | O | 내 정보·언어·탈퇴 | |
| `POST /hospitals/{id}/booking-requests` | **O** | 요청서 제출 + 동의 | 필수 동의 없으면 422 |
| `GET /me/booking-requests` · `/{id}` | O | 내 요청 목록·상태·승인된 답장 | 남의 요청은 404 |
| `POST /me/booking-requests/{id}/accept` · `/cancel` | O | 제안 수락·취소 | |

### 병원용 (`apps/web-hospital`, 직원 로그인)

| 메서드·경로 | 하는 일 | 주의 |
|---|---|---|
| `POST /auth/staff/login` | 직원 로그인 | 비밀번호 해시 |
| `GET /tenant/booking-requests?from=&to=&status=` | 캘린더·문의함 목록 | **내 병원 것만** |
| `GET /tenant/booking-requests/{id}` | 상세(원문+번역, AI 요약) | |
| `POST /tenant/booking-requests/{id}/confirm` · `/reject` · `/propose` | 상태 변경 | 이력 기록 |
| `POST /tenant/booking-requests/{id}/reply-draft` | AI 답장 초안 생성 | 발송 안 함 |
| `POST /tenant/replies/{id}/approve` | 직원 승인 → 번역·발송 | audit 기록 |
| `GET·PUT /tenant/availability` | 가용 시간 | |
| `GET /tenant/audit-logs`, `GET /tenant/usage` | 자동화 기록, AI 사용량 | 목업 가능 |

## 8. 더 생각해야 할 개념

| 개념 | 왜 | 제안 |
|---|---|---|
| **시간대(timezone)** | 환자는 해외(대만·베트남)에서 요청, 병원은 한국 시간 → 날짜가 하루 밀릴 수 있음 | DB는 **UTC**(`timestamptz`), 병원 화면은 Asia/Seoul, 환자 화면은 환자 시간대 + "한국 시간" 병기 |
| **값은 코드, 글자는 프론트** | i18n 범위 정리 결과 | API는 `status: "pending"`, `day: "mon"`처럼 **코드만**, 번역은 프론트 i18n. 데이터 값(병원명 로마자·영문 주소)만 DB에 언어별 칸 |
| **원문·번역 병기** | 원문 그대로 번역 + 병기 + "기계 번역" 표시 ([규제-1대1상담.md](../research/의료관광/규제-1대1상담.md) 3-1절) | 텍스트 칸은 항상 `original`, `translated`, `lang`, `machine_translated` 한 묶음 |
| **AI 호출은 백그라운드** | LLM 응답이 느림 → 요청서 제출이 멈추면 안 됨 | 제출은 바로 저장, 번역·요약은 FastAPI `BackgroundTasks`. 무거운 작업이 늘면 Celery 같은 작업 큐 검토 (FastAPI 문서 권고) [T2] |
| **LLM 전 마스킹** | 무료 엔드포인트는 입력이 기록됨, 국외 이전 (제28조의8) | 모든 AI 호출은 `ai/llm/client.py` 한 곳 → `safety.py`에서 이메일·연락처 마스킹 후 전송 |
| **tenant 격리** | 수탁자는 위탁받은 업무 범위를 넘어 이용·제공 금지 (제26조 제5항) | 병원용 API는 **로그인 직원의 tenant_id로 자동 필터** (공통 의존성) |
| **환자·직원 토큰 분리** | 환자 토큰으로 병원 API를 부르면 안 됨 | 토큰에 `role: patient/staff` 넣고, 라우터별 의존성으로 확인 |
| **안전조치** | 민감정보는 안전성 확보 조치 필요 (제23조 제2항, 제29조) | 비밀번호·인증코드는 해시, 건강정보 칸은 접근 기록, `.env`는 git 제외(현재 .gitignore) |
| **데이터 기준일** | 공공 데이터는 수집일 기준(2026-10-28) | 모든 공공 정보 응답에 `source`, `fetched_at` → 화면 표시 |
| **에러 형식 통일** | 프론트 2개가 같은 방식으로 처리 | `{code, message, detail}`, `code`는 i18n 키 |
| **API 버전** | 프론트·백 동시 개발 | `/api/v1`, OpenAPI 바뀌면 `shared-types` 재생성 |

## 9. 팀이 정할 것

| 항목 | 선택지 | 제안 |
|---|---|---|
| 로컬 DB 실행 | Docker Compose / 각자 설치 / 공용 호스팅 | Docker Compose (팀원 PC에서 Docker Desktop 되는지 먼저 확인) |
| ORM·마이그레이션 | SQLAlchemy 2 + Alembic / SQLModel | SQLAlchemy 2 + Alembic [T5][T6] |
| 토큰 방식 | JWT / 세션 쿠키 | JWT (환자·직원 공통, `role`로 구분) |
| 메일 발송 | 콘솔 출력 / 무료 메일 API | 11/9까지 콘솔, 시연 전 결정 |
| 시연 위치 | 로컬 노트북 / 무료 호스팅 | 12/9 시연 환경 먼저 정하기 |
| `proposed` 거절 후 상태 | `rejected` / `pending` 재요청 | 5절 |
| 요청서 보관 기간 | — | 질의 회신 후 |

## 10. 일정 (plan.md 8절에 맞춤)

| 기간 | 백엔드 할 일 | 완료 기준 |
|---|---|---|
| ~11/4 | 이 문서 확정, `docker-compose.yml`, `main.py`·`core/`·DB 연결·Alembic 첫 마이그레이션 | 팀원 모두 `docker compose up` + 서버 실행, `GET /api/v1/health` 동작 |
| 11/5~8 | `auth`(환자 인증코드·직원 로그인), `patient`, `booking`(제출·목록·확정·거절·제안), `consent`, `seed_demo.py`(가상 병원 3곳·가상 환자) | **로그인 → 요청서 → 병원 캘린더 "대기" → 확정 → 환자 화면 반영** (11/9 시연) |
| 11/10~16 | `hospital` 검색·필터·거리 정렬, `load_hospitals.py`, `price` 통계 | 정보 웹 목록·지도·상세가 공공 데이터로 표시 |
| 11/17~23 | `agent` API(번역·요약·답장 초안·시간 제안), `audit`, 승인 흐름, `availability` | 답장 초안 → 직원 승인 → 환자 언어로 표시 |
| 11/24~30 | `chatbot`(pgvector), `notification`, 남용 방지, 탈퇴·파기 스크립트 | 거절 질문 테스트 통과 |
| 12/1~7 | 통합 테스트, `subscription`·`usage` 목업, `shared-types` 최종 | 시연 시나리오 끝까지 오류 없음 |

## 11. 테스트로 지킬 규칙 (예시)

- 로그인 없이 요청서 제출 → **401**
- 환자 토큰으로 `confirm` 호출 → **403**
- 환자 A가 환자 B의 요청 조회 → **404**
- 병원 A 직원이 병원 B 요청 조회 → **404**
- 건강정보 칸이 있는데 `health` 동의 없음 → **422**
- `GET /hospitals?sort=` 에 `distance`·`name` 외 값 → **422** (구독 우대 정렬 방지)
- 미승인 답장은 환자 API에 **안 보임**
- 기관 5곳 미만 가격 통계는 **응답에 없음**

## 12. v1 → v2 바뀐 점

| 항목 | v1 | v2 |
|---|---|---|
| DB | 11/9까지 SQLite, 이후 PostgreSQL | **PostgreSQL + pgvector 처음부터**, Docker Compose |
| 환자 식별 | 요청마다 조회 토큰 링크 | **환자 계정(이메일 인증코드)**, 열람은 로그인 X |
| 모듈 | — | `patient/` 추가, `auth`를 로그인 공통으로 |
| 챗봇 벡터 | pgvector / Chroma / FAISS 중 선택 | pgvector로 결정 |
| 데이터 수치 | 병원 4,242곳 | + 시군구 9·종별 13, 비급여 607개 중 5곳 이상 402개 (직접 재집계) |
| 조문 | 번호만 | 원문 확인 후 항·호까지 표시 (제16조①, 제22조①, 제22조의2①, 제23조①1·②, 제26조⑤, 제28조의8①1, 제29조) |

## 출처
- 개인정보 보호법 (제16·21·22·22조의2·23·26·28조의8·29조, 2026-10-30 원문 확인): https://www.law.go.kr/법령/개인정보보호법
- 의료법 (제15조 진료거부 금지, 제27조 제3항 소개·알선·유인 금지, 2026-10-30 원문 확인): https://www.law.go.kr/법령/의료법
- 건강보험심사평가원 병원정보서비스·비급여진료비정보조회서비스 (`data/interim/영업정보/`, 2026-10-28 수집, 수치는 CSV 직접 집계): https://www.data.go.kr/data/15001698/openapi.do
- [T1] pgvector (Docker 이미지 `pgvector/pgvector`, Postgres 13+, `CREATE EXTENSION vector`): https://github.com/pgvector/pgvector
- [T2] FastAPI Background Tasks (Caveat: 무거운 작업은 Celery 등): https://fastapi.tiangolo.com/tutorial/background-tasks/
- [T3] openapi-typescript (OpenAPI 3.0·3.1 → TypeScript): https://openapi-ts.dev/
- [T4] FastAPI Bigger Applications (APIRouter·include_router): https://fastapi.tiangolo.com/tutorial/bigger-applications/
- [T5] SQLAlchemy 2.0 ORM: https://docs.sqlalchemy.org/en/20/orm/
- [T6] Alembic: https://alembic.sqlalchemy.org/en/latest/
