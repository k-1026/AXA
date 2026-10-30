# backend-plan.md — 백엔드 기획 (초안)

> 작성 2026-10-30 · 근거: [plan.md](../subject/plan.md) 3·4·5·7·8절, [compliance.md](compliance.md), [agent-spec.md](agent-spec.md), [폴더구조-v2-검토.md](../research/기술/폴더구조-v2-검토.md), [다국어-번역-범위.md](../research/기술/다국어-번역-범위.md)
> 상태: **제안**. 스택(FastAPI)만 팀 결정, 나머지는 팀 검토 필요

## 0. 한 줄 요약

백엔드가 하는 일은 3가지:
1. 공공 병원 정보를 **읽기 전용**으로 제공
2. 예약 **요청서**를 받아 상태를 관리 (`대기 → 확정·거절·시간 제안`)
3. AI 기능(번역·요약·답장 초안·챗봇)을 **기록·승인 절차**와 함께 호출

## 1. 지금 폴더 구조 점검

현재 `backend/src/modules/`에는 `hospital/ price/ auth/ booking/ tenant/ subscription/ agent/`가 **빈 폴더**로만 있음.

### 1-1. 빠진 것 (추가 필요)

| 빠진 것 | 왜 필요한가 | 제안 위치 |
|---|---|---|
| **앱 진입점·공통 설정** | FastAPI 앱, DB 연결, 환경변수, CORS(앱 2개), 에러 형식 | `backend/src/main.py`, `backend/src/core/` |
| **DB 테이블 정의·마이그레이션** | 테이블 구조를 바꿀 때 팀원 DB가 같이 바뀌어야 함 | `modules/*/models.py` + `backend/alembic/` |
| **동의(consent)** | 개인정보·건강정보 **별도 동의**의 기록(무엇에, 어떤 문구 버전에, 언제) — 나중에 증명해야 함 (개인정보보호법 제22·23조) | `modules/consent/` |
| **기록(audit / automation-log)** | 화면(`web-hospital/automation-log`)은 있는데 저장하는 백엔드가 없음. "직원 승인 후 발송" 증명 | `modules/audit/` |
| **알림(notification)** | 병원이 확정·거절·제안하면 환자에게 알려야 함. 환자는 회원이 아님 → 이메일 or 상태 확인 링크 | `modules/notification/` |
| **챗봇 API** | `ai/chatbot`은 있는데 웹에서 부를 엔드포인트가 없음 | `modules/chatbot/` (얇은 래퍼) |
| **가용 시간(availability)** | `ai/agent/tools/schedule.py`가 "예약 가능 시간"을 제안하려면 병원 근무·예약 가능 시간 데이터가 있어야 함 | `modules/booking/` 안 또는 `modules/availability/` |
| **데이터 적재 스크립트** | `data/processed/` 병원 마스터 → DB로 넣기, 가상 데모 데이터 넣기 | `backend/scripts/load_hospitals.py`, `seed_demo.py` |
| **OpenAPI 내보내기** | `packages/shared-types`를 자동 생성하려면 스키마 파일을 뽑는 단계가 필요 | `backend/scripts/export_openapi.py` |
| **테스트** | 규제 규칙(정렬, 상태 권한, 동의 필수)이 깨지지 않는지 자동 확인 | `backend/tests/` |

### 1-2. 이름·역할 정리가 필요한 것

| 폴더 | 문제 | 제안 |
|---|---|---|
| `modules/agent/` vs `ai/agent/` | 둘 다 "agent" → 역할 혼동 | `ai/agent` = 도구·프롬프트(로직), `backend/modules/agent` = **API + 승인·기록**만. README 한 줄씩 |
| `modules/tenant/` vs `modules/auth/` | 병원 계정·직원 계정이 어디 있는지 애매 | `tenant` = 병원(구독 단위), `auth` = 직원 로그인·권한 |
| `modules/price/` | 병원별 가격이 아니라 **지역 통계**만 (가격-표시-방식) | 이름은 유지, 테이블은 `price_stats`(미리 계산) |
| `backend` ↔ `ai` 연결 | 백엔드가 `ai/` 코드를 어떻게 부르는지 안 정함 | **같은 Python 프로세스에서 import** (데모 규모엔 별도 서버 불필요). 루트에 `pyproject.toml` 하나 |

### 1-3. 모듈 안 파일 규칙 (모든 모듈 공통)

```
modules/booking/
├── router.py       # URL·HTTP (FastAPI 라우터)
├── schemas.py      # 요청·응답 모양 (Pydantic) → OpenAPI → TS 타입
├── models.py       # DB 테이블 (SQLAlchemy)
├── service.py      # 규칙 (상태 변경 가능 여부, 권한, 동의 확인)
└── repository.py   # DB 읽기·쓰기 (선택, 작으면 service에 합침)
```
- **규제 규칙은 `service.py`에** 둔다 → 테스트가 쉬움 (예: "환자 쪽은 `confirmed`로 못 바꿈")

## 2. 제안 구조 (수정본)

```
backend/
├── pyproject.toml          # (또는 루트 하나)
├── alembic/                # DB 마이그레이션
├── scripts/
│   ├── load_hospitals.py   # data/processed → DB
│   ├── seed_demo.py        # 가상 병원 3곳·가상 요청
│   └── export_openapi.py   # → packages/shared-types
├── src/
│   ├── main.py
│   ├── core/               # config.py db.py security.py errors.py
│   └── modules/
│       ├── hospital/       # 공공 병원 정보 (읽기 전용) + 검색·필터
│       ├── price/          # 지역 가격 통계 (읽기 전용)
│       ├── booking/        # 요청서·상태·답장·가용 시간
│       ├── consent/        # 동의 기록         ← 추가
│       ├── notification/   # 환자 알림         ← 추가
│       ├── auth/           # 직원 로그인·역할
│       ├── tenant/         # 병원 계정(등록 여부), 데이터 격리
│       ├── subscription/   # 플랜·좌석·AI 사용량 (목업)
│       ├── agent/          # AI 도구 호출 API + 승인
│       ├── chatbot/        # 챗봇 API          ← 추가
│       └── audit/          # 자동화·승인 기록   ← 추가
└── tests/
```

## 3. 데이터 모델 (초안)

### 3-1. 공공 정보 (읽기 전용, ETL로 채움)

| 테이블 | 주요 칸 | 비고 |
|---|---|---|
| `hospitals` | id, ykiho, 이름(한글·로마자), 종별, 시군구, 주소(한글·영문), 전화, 위도·경도, 홈페이지, 등록 유치기관 여부, 인증 여부, `is_demo`, 출처, 수집일 | 원천: `daegu_hospitals.csv` (4,242행). 시연은 `is_demo=true` 가상 병원 |
| `hospital_departments` | hospital_id, 진료과 코드 | 필터용 |
| `hospital_hours` | hospital_id, 요일, 시작·끝(정규화 `HH:MM`), 점심, 메모(한글 원문), 휴진 상태(`closed/open/emergency_only/unknown`), 출처, 확인일 | 원천: `daegu_hospital_hours.csv`. 메모는 번역 안 하고 원문 |
| `nonpay_items` | 코드, 한글명, 영어·번체·베트남어명, 검수 여부 | 원천: `nonpay_item_codes.csv`. 미리 번역 |
| `price_stats` | 항목 코드, 지역, 기관 수, 중앙값, 사분위, 기준일 | `daegu_nonpay_prices.csv`에서 **미리 계산**. 기관 5곳 미만은 저장 안 함 |

### 3-2. 서비스 데이터 (개인정보 포함 → 보호 필요)

| 테이블 | 주요 칸 | 규칙 |
|---|---|---|
| `tenants` | id, hospital_id, 등록번호, 플랜, 요청 기능 on/off | 요청 기능은 **등록 유치의료기관만** on |
| `staff_users` | id, tenant_id, 이메일, 비밀번호 해시, 역할(`owner/staff`) | 다른 tenant 데이터 조회 불가 |
| `booking_requests` | id, **조회 토큰**, hospital_id, 상태, 환자 언어, 국적, 연락 방법·연락처, 희망 날짜 후보(여러 개), 진료과, 비자 필요 여부, 자유 입력 원문·한국어 번역, 건강정보(선택), 생성 시각, 환자 시간대 | 상태 기본값 `pending` |
| `booking_events` | request_id, 이전→다음 상태, 누가(직원 id / 환자), 제안 시간, 시각 | **상태 이력** (지우지 않음) |
| `replies` | request_id, 종류(템플릿/자유), 한국어 원문, 번역문, AI 초안 여부, 승인 직원, 발송 시각 | 승인 없으면 발송 X |
| `consents` | request_id, 종류(`privacy/health/overseas_transfer`), 문구 버전, 언어, 동의 시각 | 건강정보 칸이 있으면 `health` 동의 필수 |
| `availability` | tenant_id, 요일·시간대 or 날짜별 슬롯 | `schedule.py` 입력 |
| `audit_logs` | tenant_id, 행위(도구 호출·발송·상태 변경), 입력·출력 참조, 승인자, 시각 | automation-log 화면 |
| `llm_usage` | tenant_id, 서비스(챗봇/에이전트), 토큰, 시각 | 구독 "AI 사용량" 기준 |

## 4. 예약 요청 상태 흐름

```
           (병원) 확정
 pending ───────────────▶ confirmed
   │  │   (병원) 거절
   │  └────────────────▶ rejected
   │   (병원) 다른 시간 제안
   └──────▶ proposed ──(환자) 수락──▶ confirmed
                │  └───(환자) 거절──▶ rejected? / pending 재요청
   (환자) 취소: pending·proposed → cancelled
   (시간 경과) 희망 날짜 지남 → expired
```

| 규칙 | 근거 |
|---|---|
| `confirmed`·`rejected`·`proposed`는 **병원 직원 계정만** | compliance.md "확정은 병원" |
| `proposed → confirmed`는 병원이 이미 제시한 시간을 환자가 받아들인 것 → 병원 결정으로 봄 | 팀 확인 필요 |
| 모든 변경은 `booking_events`에 남김 | 질의 회신·분쟁 대비 |

**정할 것**: 환자가 제안을 거절하면 `rejected`로 끝낼지, 새 희망 날짜로 `pending`에 돌릴지

## 5. API 목록 (초안)

### 환자용 (`apps/web-platform`, 로그인 없음)

| 메서드·경로 | 하는 일 | 주의 |
|---|---|---|
| `GET /hospitals` | 검색·필터(지역·진료과·요일·시간·휴진·등록·요청 가능), 정렬(`distance`·`name`만) | 구독 여부로 정렬 X |
| `GET /hospitals/{id}` | 상세 + 진료시간 + 출처·확인일 + 전화·이메일 | 다른 연락 경로 항상 포함 |
| `GET /prices/stats?item=&region=` | 지역 통계 | 5곳 미만 숨김 |
| `POST /hospitals/{id}/booking-requests` | 요청서 제출 + 동의 | 동의 없으면 422, 응답에 조회 토큰 |
| `GET /booking-requests/{token}` | 상태·병원 답장 확인 | 토큰 = 비밀번호 역할 |
| `POST /booking-requests/{token}/accept` · `/cancel` | 제안 수락·취소 | |
| `POST /chatbot/ask` | 챗봇 질문 | 출처·기준일 포함 응답, 의료 판단 거절 |

### 병원용 (`apps/web-hospital`, 직원 로그인)

| 메서드·경로 | 하는 일 | 주의 |
|---|---|---|
| `POST /auth/login` | 직원 로그인 | |
| `GET /tenant/booking-requests?from=&to=&status=` | 캘린더·문의함 목록 | **내 병원 것만** |
| `GET /tenant/booking-requests/{id}` | 상세(원문+번역, AI 요약) | |
| `POST /tenant/booking-requests/{id}/confirm` · `/reject` · `/propose` | 상태 변경 | 이력 기록 |
| `POST /tenant/booking-requests/{id}/reply-draft` | AI 답장 초안 생성 | 발송 안 함 |
| `POST /tenant/replies/{id}/approve` | 직원 승인 → 번역·발송 | audit 기록 |
| `GET·PUT /tenant/availability` | 가용 시간 | |
| `GET /tenant/audit-logs`, `GET /tenant/usage` | 자동화 기록, AI 사용량 | 목업 가능 |

## 6. 더 생각해야 할 개념

| 개념 | 왜 | 제안 |
|---|---|---|
| **시간대(timezone)** | 환자는 해외(대만·베트남)에서 요청, 병원은 한국 시간. 날짜가 하루 밀릴 수 있음 | DB는 **UTC 저장**, 병원 화면은 Asia/Seoul, 환자 화면은 환자 시간대 + "한국 시간" 병기 |
| **환자 식별 (비회원)** | 환자 회원가입은 MVP 범위 밖 | 요청마다 **추측 불가능한 조회 토큰**(링크). 연락처 확인(이메일 인증)은 확장 |
| **값은 코드, 글자는 프론트** | i18n 범위 정리 결과 | API는 `status: "pending"`, `day: "mon"`처럼 **코드만** 내려주고 번역은 프론트 i18n. 데이터 값(병원명 로마자·영문 주소)만 DB에 언어별 칸 |
| **원문·번역 병기** | 번역은 원문 그대로 + 병기 + "기계 번역" 표시 (규제-1대1상담 3-1절) | 텍스트 칸은 항상 `original`, `translated`, `lang`, `machine_translated` 한 묶음 |
| **AI 호출은 비동기** | LLM 응답이 느림(수 초). 요청서 제출이 AI 때문에 멈추면 안 됨 | 제출은 바로 저장 → 번역·요약은 **백그라운드 작업**(FastAPI BackgroundTasks), 끝나면 상태 갱신 |
| **LLM 전 마스킹** | 무료 엔드포인트는 입력이 기록됨, 국외 이전 (제28조의8) | 모든 AI 호출은 `ai/llm/client.py` 한 곳 → `safety.py`에서 이름·연락처 마스킹 후 전송 |
| **tenant 격리** | 수탁자 범위 밖 이용 금지 (제26조 제5항) | 병원용 API는 **로그인 직원의 tenant_id로 자동 필터** (쿼리마다 손으로 넣지 않게 공통 의존성) |
| **개인정보 보관 기간·파기** | 목적 달성 후 지체 없이 파기 (제21조) | 요청서 보관 기간을 정하고 지난 건 자동 삭제·익명화 스크립트 (기간은 팀·질의 회신 후) |
| **스팸·남용 방지** | 비회원 제출 → 병원에 가짜 요청 폭탄 가능 | IP·연락처 기준 제출 횟수 제한, 같은 병원 중복 요청 막기 |
| **데이터 기준일** | 공공 데이터는 수집일 기준 (2026-10-28) | 모든 공공 정보 응답에 `source`, `fetched_at` 포함 → 화면 표시 |
| **에러 형식 통일** | 프론트 2개가 같은 방식으로 처리 | `{code, message, detail}` + 코드는 i18n 키 |
| **API 버전** | 프론트·백 동시 개발 | 경로 앞에 `/api/v1`, OpenAPI 바뀌면 `shared-types` 재생성 |

## 7. 팀이 정할 것

| 항목 | 선택지 | 제안 |
|---|---|---|
| DB | SQLite / PostgreSQL | **11/9까지 SQLite** (설치 없음) → 배포 필요하면 PostgreSQL. SQLAlchemy라 코드 거의 그대로 |
| ORM·마이그레이션 | SQLAlchemy 2 + Alembic / SQLModel | SQLAlchemy 2 + Alembic (자료 많음) |
| 직원 인증 | JWT / 세션 쿠키 | 데모는 JWT 간단 구현, 비밀번호 해시 필수 |
| 챗봇 벡터 저장소 | pgvector / Chroma(파일) / FAISS | PostgreSQL 안 쓰면 Chroma 파일 |
| 시연 위치 | 로컬 노트북 / 무료 호스팅 | 12/9 시연 환경 먼저 정하기 (발표 PC에서 돌아가야 함) |
| `proposed` 거절 후 상태 | `rejected` / `pending` 재요청 | 4절 |
| 요청서 보관 기간 | — | 질의 회신 후 |

## 8. 일정 (plan.md 8절에 맞춤)

| 기간 | 백엔드 할 일 | 완료 기준 |
|---|---|---|
| ~11/4 | 이 문서 팀 확정, `main.py`·`core/`·DB 연결, 모듈 파일 규칙 | `GET /health` 동작, 팀원 모두 로컬 실행 |
| 11/5~8 | `booking`(제출·목록·확정·거절·제안), `consent`, `auth` 최소, `seed_demo.py`(가상 병원 3곳) | **요청서 → 병원 캘린더 "대기" → 확정 → 환자 상태 화면** (11/9 시연) |
| 11/10~16 | `hospital` 검색·필터·거리 정렬, `load_hospitals.py`(processed → DB), `price` 통계 | 정보 웹 목록·지도·상세가 실제 공공 데이터로 표시 |
| 11/17~23 | `agent` API(번역·요약·답장 초안·시간 제안), `audit`, 승인 흐름, `availability` | 답장 초안 → 직원 승인 → 환자 언어로 표시 |
| 11/24~30 | `chatbot` API, `notification`, 남용 방지, tenant 격리 테스트 | 거절 질문 테스트 통과 |
| 12/1~7 | 통합 테스트, `subscription`·`usage` 목업, OpenAPI → `shared-types` 최종 | 시연 시나리오 끝까지 오류 없음 |

## 9. 테스트로 지킬 규제 규칙 (예시)

- 환자 API로 상태를 `confirmed`로 바꾸면 **거부**
- 건강정보 칸이 있는데 `health` 동의가 없으면 **제출 거부**
- 병원 A 직원이 병원 B 요청을 조회하면 **404**
- `GET /hospitals?sort=` 에 `distance`·`name` 외 값이면 **거부** (구독 우대 정렬 방지)
- 미승인 답장은 환자 조회 API에 **안 보임**
- 기관 5곳 미만 가격 통계는 **응답에 없음**

## 출처
- 개인정보 보호법 (제21조 파기, 제22·23조 동의·민감정보, 제26조 위탁, 제28조의8 국외 이전): https://www.law.go.kr/법령/개인정보보호법
- 의료법 (제15조, 제27조): https://www.law.go.kr/법령/의료법
- 건강보험심사평가원 병원정보서비스 (`data/interim/영업정보/`, 2026-10-28 수집): https://www.data.go.kr/data/15001698/openapi.do
- FastAPI Background Tasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
- FastAPI Bigger Applications (라우터 분리): https://fastapi.tiangolo.com/tutorial/bigger-applications/
- SQLAlchemy 2.0 ORM: https://docs.sqlalchemy.org/en/20/orm/
- Alembic: https://alembic.sqlalchemy.org/en/latest/
- openapi-typescript: https://openapi-ts.dev/
