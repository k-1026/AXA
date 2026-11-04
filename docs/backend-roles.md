# backend-roles.md — 백엔드 2인 역할 분담 (제안)

> 작성 2026-10-30 · 기준: [backend-plan.md](backend-plan.md) v2 (모듈·API·일정)
> 이름 대신 **백엔드 A / 백엔드 B**로 표기 (공개 저장소, 실명 X). 팀이 누가 A·B인지 정해서 로컬 `subject/팀공유.md`에만 기록 (커밋 X)

## 0. 나누는 원칙

1. **화면(사용자) 기준으로 세로로 나눈다**: A = 환자 쪽(`web-platform`이 부르는 API), B = 병원 쪽(`web-hospital`이 부르는 API)
   → 프론트 담당과 짝이 명확하고, 같은 파일을 동시에 고칠 일이 적음
2. **공통 기반(`core/`, DB, 인증 틀)은 첫 주에 둘이 같이** 만들고, 이후 수정은 PR로만
3. **겹치는 모듈(`booking`)은 주인 1명**을 정하고, 다른 사람은 PR로 요청
4. **API 모양(`schemas.py`)을 먼저 합의**하고 구현 → 프론트도 가짜 데이터로 먼저 개발 가능

## 1. 담당 모듈

| 모듈 | 주인 | 내용 | 비고 |
|---|---|---|---|
| `core/` (config·db·security·errors) | **A+B 같이** (첫 주) | 앱 진입점, DB 연결, 토큰 검증 의존성, 에러 형식 | 이후 수정은 PR + 상대 리뷰 필수 |
| `docker-compose.yml`, `alembic/` | **B** | PostgreSQL+pgvector, 마이그레이션 | 마이그레이션 파일은 **B만 생성** (충돌 방지). A는 모델 변경을 PR로 요청 |
| `auth/` | **A** | 환자 인증코드, 직원 로그인, JWT(`role: patient/staff`) | 직원 로그인도 A (토큰 발급 로직을 한 곳에) |
| `patient/` | A | 환자 계정·`/me`·탈퇴 | |
| `consent/` | A | 동의 저장·필수 동의 확인 함수 | B는 이 함수를 가져다 씀 |
| `hospital/` | A | 공공 병원 검색·필터·거리 정렬·상세 | |
| `price/` | A | 가격 통계 조회 | 통계 계산은 데이터 담당과 협의 |
| `chatbot/` | A | 챗봇 API 래퍼, pgvector 검색 연결 | 답변 로직은 `ai/chatbot` (AI 담당) |
| `notification/` | A | 인증코드 메일, 상태 변경 알림 (데모는 콘솔) | B는 `notify()` 함수만 호출 |
| `booking/` **models·service(상태 흐름)** | **B (주인)** | 테이블, 상태 전이 규칙, `booking_events` | A가 쓰는 함수: `create_request()`, `list_for_patient()`, `accept()`, `cancel()` |
| `booking/` 환자용 router | A | `POST /hospitals/{id}/booking-requests`, `/me/booking-requests/...` | B의 service 함수 호출만 |
| `booking/` 병원용 router | B | `/tenant/booking-requests/...` 확정·거절·제안 | |
| `availability` (booking 안) | B | 병원 가용 시간 | |
| `tenant/` | B | 병원 계정·직원·**tenant 격리 의존성** | |
| `agent/` | B | AI 도구 호출 API, 답장 승인 흐름 | 도구 로직은 `ai/agent` (AI 담당) |
| `audit/` | B | 자동화·승인 기록 | A의 기능도 기록이 필요하면 `log_action()` 호출 |
| `subscription/`, `/tenant/usage` | B | 플랜·AI 사용량 (목업) | |
| `scripts/load_hospitals.py` | A | 공공 데이터 → DB | `data/` 담당과 같이 |
| `scripts/seed_demo.py` | B | 가상 병원 3곳·직원·가상 환자·가상 요청 | A는 환자 쪽 가상 데이터 추가 PR |
| `scripts/export_openapi.py` | A | OpenAPI → `packages/shared-types` | |
| `tests/` | **각자 자기 모듈** | backend-plan 11절 규칙 | 격리 테스트(남의 요청 404)는 **상대가 작성** (교차 검증) |

**양 비교**: A = 모듈 수가 많지만 대부분 조회(읽기). B = 모듈 수는 적지만 상태 흐름·권한·AI 승인처럼 규칙이 많음 → 대체로 균형. 11/24 이후 남는 쪽이 테스트·통합을 더 맡음

## 2. 주차별 할 일

| 기간 | 백엔드 A (환자 쪽) | 백엔드 B (병원 쪽) | 같이 |
|---|---|---|---|
| ~11/4 | `auth` 틀(JWT 발급·검증), `core/security.py` | `docker-compose.yml`, `core/db.py`, Alembic 첫 마이그레이션 | `main.py`·`core/` 구조, **booking·consent 스키마 합의**, 브랜치 규칙 |
| 11/5~8 | 환자 인증코드 로그인, `patient`, `consent`, 요청서 제출 API | `booking` 모델·상태 흐름, 확정·거절·제안 API, `tenant` 최소, `seed_demo.py` | **11/9 시연 흐름 연결 테스트** (로그인 → 제출 → 캘린더 대기 → 확정 → 환자 화면) |
| 11/10~16 | `hospital` 검색·필터·거리 정렬, `load_hospitals.py`, `price` | `availability`, tenant 격리 의존성 정리, 직원 계정 관리 | `shared-types` 첫 생성, 프론트와 API 점검 |
| 11/17~23 | `notification`(상태 변경 알림), 남용 방지(횟수 제한) | `agent` API(번역·요약·답장 초안·시간 제안), 승인 흐름, `audit` | AI 담당과 `ai/llm/client.py` 호출 방식 맞추기 |
| 11/24~30 | `chatbot` API + pgvector 검색, 탈퇴·파기 스크립트 | `subscription`·`usage` 목업, `llm_usage` 기록 | 교차 테스트(상대 모듈의 권한·격리 테스트 작성) |
| 12/1~7 | 통합 테스트, OpenAPI 최종 | 통합 테스트, 시연 데이터 정리 | 시연 시나리오 리허설 |

## 3. 같이 정해야 하는 "약속" (11/4 전에)

| 약속 | 내용 | 왜 |
|---|---|---|
| booking 스키마 | 요청서 입력 칸, 상태 코드(`pending/confirmed/rejected/proposed/cancelled/expired`), 응답 모양 | A·B·프론트 2명이 모두 씀 |
| 함수 경계 | `create_request()`, `change_status()`, `require_consent()`, `notify()`, `log_action()`의 입력·출력 | 서로의 모듈 안을 고치지 않고 호출만 |
| 토큰 내용 | `sub`, `role`, `tenant_id`(직원만), 만료 | 두 사람의 의존성이 같은 토큰을 읽음 |
| 에러 코드 | `{code, message, detail}` + 코드 목록 | 프론트 i18n 키 |
| 테스트 DB | 테스트는 별도 DB(또는 트랜잭션 롤백) | 개발 데이터 안 깨지게 |

## 4. 브랜치·리뷰 규칙

```
main  ←(PR, 리더 승인)─  backend  ←(PR, 상대 리뷰)─  backend-A-auth, backend-B-booking ...
```

- 각자 `backend`에서 **작업 브랜치**를 따서 작업 → `backend`로 PR → **상대 백엔드가 리뷰** 후 머지
- `backend` → `main`은 기능 묶음이 끝날 때(예: 11/8 시연 흐름 완성) PR → 리더 승인 (CODEOWNERS)
- 공통 파일(`core/`, `alembic/versions/`, `docker-compose.yml`, `booking/models.py`)을 고치는 PR은 **반드시 상대 승인**
- 마이그레이션 충돌 방지: 모델 바꾸는 PR은 하루 1~2개로 모아서, 머지 전 `alembic upgrade head` 확인
- 커밋 전 `.env` 제외 확인, 실명·API 키 X (저장소 규칙)

## 5. 다른 팀원과 맞닿는 곳

| 상대 | 맞닿는 곳 | 백엔드 쪽 담당 |
|---|---|---|
| 정보 웹 프론트 | `/hospitals`, `/prices`, `/me`, 요청서, 챗봇 | A |
| 병원 대시보드 프론트 | `/tenant/...`, 캘린더, 승인 | B |
| AI 담당 | `ai/llm/client.py`, `ai/agent/tools`, `ai/chatbot` | 에이전트 = B, 챗봇 = A |
| 데이터 담당 | `data/processed` 병원 마스터, 가격 통계 | A (`load_hospitals.py`) |

## 6. 바꿔도 되는 부분

- 한 명이 FastAPI·DB 경험이 더 많으면 **B(상태 흐름·권한·마이그레이션)**를 맡는 게 안전
- 프론트와 짝이 바뀌면 A·B 경계도 같이 조정 (예: 병원 대시보드 프론트가 늦으면 B가 `seed_demo`·통합 테스트 비중 ↑)
- 11/9 시연 후 진행 상황 보고 2주 차 분담 재조정

## 출처
- 모듈·API·일정: [backend-plan.md](backend-plan.md), [plan.md](../subject/plan.md) 8절
- 브랜치 보호·CODEOWNERS: GitHub Docs, About protected branches: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- GitHub Docs, About code owners: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
