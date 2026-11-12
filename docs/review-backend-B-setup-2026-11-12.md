# backend-B-setup 검토 — main 합치기 전 (2026-11-12)

비교 기준: 내 작업 폴더(`backend-B-setup`, 커밋 안 한 변경 포함) ↔ `main` = `origin/backend` (`4505b75`)

## 1. 한 줄 결론
- **커밋한 것**(`ad317be`, todo-B 체크리스트): main에 없음, 합쳐도 충돌 없음
- **커밋 안 한 10/30 셋업 코드**: 11/4 결정 12·13(Docker → Supabase, 마이그레이션은 A 담당) 이후 A가 같은 파일을 새로 만들어서 **대부분 쓸모가 없어짐**. 그대로 두면 main을 합칠 수 없음 (git이 덮어쓰기를 거부함)
- 버리기 전에 살릴 만한 것이 3가지 있음 (4절)

## 2. 파일별 상태

| 파일 | main에 | 차이 | 판단 |
|---|---|---|---|
| `docker-compose.yml` | 없음 (결정 12로 삭제) | — | ❌ 버림. 로컬 Docker를 쓰지 않음 |
| `alembic/versions/20261030_0001_enable_pgvector.py` | 다른 `0001` 있음 | revision `"0001"`이 main의 `0001_patient_consent`와 같음 | ❌ **위험.** 두 head가 생겨 `alembic upgrade`가 실패함. 마이그레이션은 이제 A 담당 |
| `alembic.ini`, `alembic/env.py`, `script.py.mako` | 있음 | 내 것: `src.` 경로 기준. main: `core.` 경로, `UTCDateTime` 렌더링, `db_models` 등록 | ❌ main이 맞음 |
| `core/config.py` | 있음 | 내 것: DB URL·CORS만. main: JWT·ECOS·CRON·루트 `.env` 절대경로 | ❌ main이 맞음 (내 것으로 바꾸면 로그인·환율이 깨짐) |
| `core/db.py` | 있음 | 내 것: import할 때 엔진 생성, 커넥션 풀 사용. main: `NullPool`·prepared statement 끔(Supabase 풀러), `UTCDateTime`, SQLite 테스트 | ❌ main이 맞음 (Vercel·Supabase에 맞춤) |
| `core/errors.py` | 있음 | 내 것에만: **HTTPException(404·405 등) → `{code,message,detail}` 변환**. main에만: 500 `internal` 안전망, 401 `WWW-Authenticate` | ⚠️ main을 기준으로 하고, 404 변환만 옮길지 검토 (4-①) |
| `main.py` | 있음 | 내 것: health에서 DB `SELECT 1` 확인(실패하면 503). main: 라우터 5개, health는 `{"status":"ok"}`만 | ⚠️ main을 기준으로 하고, DB 확인은 검토 (4-②) |
| `src/__init__.py`, `core/__init__.py`, `tests/__init__.py` | 없음 | 내 것은 `src.core…` 패키지 방식. main은 `core…` (pythonpath `backend/src`) | ❌ 버림. 섞이면 import가 꼬임 |
| `tests/conftest.py` | 있음 | main: 메모리 SQLite + 가짜 JWT 비밀값 | ❌ main이 맞음 |
| `tests/test_health.py` | 없음 | `src.` import + 실제 DB 필요 | ❌ 그대로는 못 씀 (4-②를 하면 main 방식으로 다시 작성) |
| `pyproject.toml` | 있음 | 내 것: pip/setuptools, Python 3.11, `pgvector`. main: uv, Python 3.12, JWT·argon2·tzdata, `ai/tests` 포함 | ❌ main이 맞음 |
| `backend/README.md` | 없음 | `docker compose`·`uvicorn src.main` 실행법 | ❌ 지금 방식과 다름. 필요하면 새로 작성 |
| `.env.example` | 있음 | 내 것: Docker DB 기본값 + 예전 LLM 항목. main: Supabase·JWT·ECOS·CRON·Gemini | ❌ main이 맞음 |
| `.gitignore` | 있음 | 내 것에만: `.pytest_cache/`, `*.egg-info/`, `.vite/` | ✅ 3줄만 옮기면 좋음 (4-③) |
| `docs/backend-worklog-B.md` | 있음 | 내 10/30 기록 12줄이 main에 없음 | ✅ 남기되 "결정 12·13으로 대체됨"을 덧붙임 |
| `docs/backend-todo-B.md` | 없음 | 셋업 항목 5개 `[x]` | ⚠️ 셋업 항목은 이제 A·결정 12로 끝남 → 표시를 고쳐야 함 (5절) |
| `CLAUDE.md`, `subject/subject.md`, `README.md`, `research/company/*`, `valuechain/*` | 있음 | **main과 똑같음** | — 합치면 main 것으로 그대로 들어옴 |

백엔드와 관계없는 새 파일(`기획서.pdf`, `subject/서비스소개-초안.md`, `data/etl/filter_4depts.mjs`, `data/processed/daegu_hospitals_4depts.json`, `.claude/launch.json`)은 main과 충돌하지 않음. 건드리지 않음.

## 3. 문제가 되는 곳 (중요한 순서)
1. **마이그레이션 revision 충돌**: 내 `0001`과 main의 `0001`이 같은 id. 둘 다 들어가면 Alembic이 실행되지 않음. 결정 13에 따라 마이그레이션 생성은 A만 함
2. **import 방식이 다름**: 내 코드는 `from src.core…`, main은 `from core…`. 파일을 일부만 섞으면 앱·테스트 시작이 실패함
3. **DB 연결 방식이 다름**: 내 `db.py`는 import할 때 바로 엔진을 만들고 풀을 씀. Supabase 트랜잭션 풀러(6543)에서는 prepared statement 오류가 나고, `DATABASE_URL`이 없으면 import만 해도 실패함
4. **설정 항목 누락**: 내 `config.py`에는 `jwt_secret`·`ecos_api_key`·`cron_secret`이 없음 → auth·fx·maintenance가 깨짐
5. **todo-B 체크 표시가 사실과 다름**: `[x]`로 한 셋업 항목이 main에는 다른 방식(A)으로 들어가 있음

## 4. 살릴 만한 것 (main 방식으로 다시 작성, 공통 파일이라 A 리뷰 필요)
1. **404·405 에러 형식 통일** — main은 없는 경로에서 FastAPI 기본값 `{"detail":"Not Found"}`를 돌려줌 → 프론트가 `code`를 못 읽음. contracts 4절의 `not_found`로 바꾸는 핸들러 추가. 405처럼 표에 없는 상태의 코드는 contracts에 먼저 추가해야 함
2. **health에서 DB 확인** — 지금은 서버만 확인함. DB 장애를 알 수 있게 `SELECT 1` + 503을 넣을지 A와 결정. 단, health를 부를 때마다 Supabase에 연결하고 기존 CORS·보안 테스트 2개가 health를 쓰므로, 별도 경로(`/health/db`)로 두는 것도 방법
3. **`.gitignore` 3줄** (`.pytest_cache/`, `*.egg-info/`, `.vite/`) — 위험 없음

참고: main의 마이그레이션에는 `CREATE EXTENSION vector`가 아직 없음. 챗봇 벡터 검색(`chatbot_chunks`)을 시작할 때 A에게 요청 (지금 할 일은 아님).

## 5. 합치는 순서 제안
1. 커밋 안 한 셋업 코드를 stash에 보관 (`git stash push -u -- backend docker-compose.yml pyproject.toml .env.example .gitignore docs`)
2. `git merge main` → 충돌 없음 (테스트 merge로 확인함)
3. worklog-B 10/30 기록을 다시 넣고 "결정 12·13으로 대체, 커밋 안 함"을 추가. todo-B 셋업 항목은 "A가 완료(결정 12)"로 수정
4. `.gitignore` 3줄 추가 (4-③)
5. push → `backend-B-setup` → `backend` PR
6. 4-①·4-②는 따로 브랜치를 만들어 A 리뷰를 받음
