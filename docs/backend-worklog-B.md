# backend-worklog-B.md — 백엔드 B 작업 기록 (병원 쪽)

> **B만 쓰는 파일** (A는 읽기만). 세션이 끝날 때마다 **맨 위에** 항목 추가. 사람이 쓰든 AI가 쓰든 같은 형식
> A에게 부탁할 것은 "A에게 요청"에 쓰고, A는 처리하면 **A의 worklog**에 "B 요청 n 처리"라고 적음

## 형식 (복사해서 아래에 추가)

```
### YYYY-MM-DD · 브랜치 · 도구(Claude/Codex/직접)
- 한 일:
- 바뀐 계약: 없음 / contracts n절
- 마이그레이션: 없음 / 리비전 id
- 테스트: 통과 n개 / 실패 내용
- 다음 할 일:
- A에게 요청:
- 막힌 것·질문:
```

## 기록

### 2026-11-12 · backend-B-health-404 · Claude
- 한 일: (1) 없는 경로 404·없는 메서드 405를 `{code, message, detail}` 형식으로 (`core/errors.py`). 코드는 `not_found`가 아니라 `api.not_found`·`api.method_not_allowed` — 프론트 `useConversations.ts`가 `not_found`를 "서버에 이미 없음"으로 보고 대화를 지우므로, 경로 오류와 섞이면 데이터를 잘못 지움. 프론트는 모르는 코드를 일반 오류로 처리하므로 프론트 변경 없음. (2) `GET /health`가 DB `SELECT 1`까지 확인, 실패하면 503 `db.unavailable` (로그엔 예외 종류만) (`main.py`)
- 바뀐 계약: contracts 4절 (에러 코드 3개), 결정 18
- 마이그레이션: 없음
- 테스트: **통과 130개** (`uv run python -m pytest backend/tests`). 추가: `test_health.py` 3개, `test_errors.py` 2개, 수정: `test_security.py::test_health` 응답
- 다음 할 일: booking 모델·상태 흐름 (todo-B 11/5~8)
- A에게 요청:
  1. **공통 파일 변경**(`core/errors.py`, `main.py`) + contracts 4절 리뷰·승인
  2. 프론트에서 `api.not_found`·`db.unavailable`을 따로 보여 줄 필요가 생기면 i18n 키 추가 (지금은 일반 오류로 충분)
- 막힌 것·질문: 이 PC는 Windows 스마트 앱 컨트롤이 켜져 있어 서명 없는 DLL이 막힘 → uv가 받은 Python(`_ctypes`)·SQLAlchemy C 확장·`psycopg-binary`가 import 실패. 보안 설정은 그대로 두고 python.org Python(서명됨) + `DISABLE_SQLALCHEMY_CEXT=1 uv sync --python <python.org python.exe> --no-binary-package sqlalchemy`로 해결. 테스트는 SQLite라 psycopg 없어도 됨 (실제 Supabase 연결·alembic은 이 PC에서 아직 안 됨)

### 2026-11-12 · backend-B-setup · Claude
- 한 일: main(4505b75) 반영. 10/30 셋업 코드는 결정 12·13(Supabase, 마이그레이션 A 담당) 이후 A가 같은 파일을 만들어 쓸모가 없어짐 → 커밋하지 않고 `git stash`에 보관. 비교 결과는 [review-backend-B-setup-2026-11-12.md](review-backend-B-setup-2026-11-12.md). `backend-todo-B.md` 기반 항목을 실제 상태로 고침, `.gitignore`에 `.pytest_cache/`·`*.egg-info/`·`.vite/` 추가
- 바뀐 계약: 없음
- 마이그레이션: 없음 (10/30의 `0001_enable_pgvector`는 main의 `0001`과 id가 겹쳐 버림)
- 테스트: 실행 안 함 (코드 변경 없음)
- 다음 할 일: booking 모델·상태 흐름 (todo-B 11/5~8)
- A에게 요청:
  1. 없는 경로 404도 `{code: "not_found", …}` 형식으로 바꿀지 (`core/errors.py`)
  2. health에 DB 연결 확인(실패 시 503)을 넣을지, 넣는다면 별도 경로로 할지
  3. 챗봇 벡터 검색을 시작할 때 `CREATE EXTENSION vector` 마이그레이션
- 막힌 것·질문: 없음

### 2026-10-30 · backend-B-setup · Claude
- 한 일: 기반 셋업 코드 작성 (docker-compose, pyproject, core/config·db·errors, Alembic 0001 pgvector, health, 테스트 3개) — **커밋 안 함. 11/4 결정 12·13으로 대체됨 (11/12 기록 참고)**
- 테스트: 미실행 (Python·Docker 미설치)

### 2026-10-30 · backend · —
- 한 일: worklog 파일 생성 (아직 코드 작업 없음)
- 다음 할 일: contracts 초안 같이 확정, `docker-compose.yml`·`core/db.py`·Alembic 첫 마이그레이션
- A에게 요청: 없음
