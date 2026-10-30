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
