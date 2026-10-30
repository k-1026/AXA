# AGENTS.md — 백엔드 공통 지침 (Claude Code · Codex 공용)

> 백엔드 2명(A·B)과 각자의 AI(Claude Code, Codex)가 **같이 읽는 단 하나의 지침**.
> 고칠 때는 이 파일만 고친다. `backend/CLAUDE.md`는 이 파일을 불러오기만 함.
> 팀 공통 규칙은 루트 `CLAUDE.md` (실명 X, 출처 없는 숫자 X, 한국어)

## 1. 작업 시작 전에 읽을 것 (순서대로)

1. `docs/backend-contracts.md` — 모듈 주인, 상태 코드, 토큰, 에러, **서로 호출하는 함수** (여기 없는 함수는 상대 모듈에서 호출 X)
2. `docs/backend-decisions.md` — 이미 정한 것 (다시 논의하지 않음)
3. `docs/backend-worklog-A.md`, `docs/backend-worklog-B.md` — **상대 최근 항목 3개**와 "상대에게 요청"
4. 필요할 때만: `docs/backend-plan.md`(전체 설계), `docs/backend-roles.md`(분담), `docs/compliance.md`(규제 경계)

## 2. 내가 A인지 B인지

- 사용자가 말한 값 → 없으면 브랜치 이름(`backend/A-…`, `backend/B-…`) → 그래도 모르면 **사용자에게 묻기**
- A = 환자 쪽 API, B = 병원 쪽 API + `booking` 주인 + 마이그레이션 ([contracts 1절](../docs/backend-contracts.md))

## 3. 브랜치

```
main ←(PR, 리더 승인)─ backend ←(PR, 상대 리뷰)─ backend/A-<기능>, backend/B-<기능>
```

- 작업 시작: `git switch backend && git pull` → `git switch -c backend/A-auth` 처럼 새 브랜치
- 작업 중 `backend`가 바뀌면 `git pull origin backend` 후 충돌 해결
- **`main`·`backend`에 직접 push 금지**. 항상 작업 브랜치 → `backend`로 PR
- `backend` → `main` PR은 사람이 결정 (AI가 임의로 만들지 않음)

## 4. 남의 파일은 고치지 않는다

| 내가 하려는 것 | 할 일 |
|---|---|
| 상대 모듈 안을 고쳐야 함 | 고치지 말고 **내 worklog "상대에게 요청"**에 적기 |
| 공유 함수·스키마·상태 코드·토큰·에러 코드 변경 | `docs/backend-contracts.md` 수정 **별도 PR** → 상대 승인 → `backend-decisions.md`에 한 줄 |
| DB 테이블 변경 | 모델(`models.py`) 변경은 해도 됨, **마이그레이션 파일은 B만 생성** |
| `core/`, `docker-compose.yml` 변경 | PR에 "공통 파일 변경" 표시, 상대 승인 필수 |

## 5. 코드 규칙

- 모듈 구조: `router.py`(HTTP) · `schemas.py`(Pydantic) · `models.py`(SQLAlchemy) · `service.py`(규칙) · `repository.py`(선택)
- **규칙은 `service.py`에**, router는 얇게. 상대 모듈은 contracts에 적힌 `service` 함수로만 호출
- 경로는 `/api/v1/...`, 응답 값은 **코드**(`"pending"`)로, 문장 번역은 프론트 i18n
- 시간은 UTC(`timestamptz`)로 저장
- 에러는 `{code, message, detail}` (contracts 4절 코드 목록에 없는 코드 만들지 않기 → 필요하면 contracts PR)
- 새 기능에는 테스트(`backend/tests/`)를 같이. 권한·격리 규칙은 반드시 테스트

## 6. 하면 안 되는 것 (규제·보안, `docs/compliance.md` 요약)

- 병원 목록 정렬에 구독·제휴·"요청 가능" 여부 반영 X (정렬은 `distance`·`name`만)
- 환자 쪽 코드에서 상태를 `confirmed`·`rejected`·`proposed`로 바꾸기 X (병원 직원만)
- AI 답장을 직원 승인 없이 환자에게 보이기·보내기 X
- 병원 API에서 다른 병원(tenant) 데이터 조회 X — tenant 필터는 공통 의존성으로
- 건강정보를 `health` 동의 없이 저장 X, 환자 계정에 건강정보 저장 X
- LLM 호출은 `ai/llm/client.py`만 사용 (마스킹 거침), **가상 데이터만**
- 실명·실제 환자 정보·API 키를 코드·테스트·시드·커밋에 넣기 X. 비밀 값은 `.env` (git 제외)
- 결제·건당 수수료·순위·추천·후기·이벤트가 기능 만들기 X

## 7. 세션을 끝낼 때 (필수)

1. **내 worklog** (`docs/backend-worklog-A.md` 또는 `-B.md`) 맨 위에 항목 추가 (형식은 그 파일 맨 위)
2. 정한 것이 생기면 `docs/backend-decisions.md`에 한 줄
3. 계약을 바꿨으면 `docs/backend-contracts.md` 변경 이력에 한 줄
4. 배운 것·정한 것은 **AI 개인 메모리에만 두지 말고 위 파일에** (상대 AI는 내 메모리를 못 봄)
5. 상대 worklog는 고치지 않음 (요청은 내 worklog에)

## 8. 커밋·PR

- 커밋 메시지: `[add]`·`[update]`·`[fix]` + 한국어 한 줄 (예: `[add] 환자 인증코드 로그인 API`)
- 커밋 전: `git status`로 `.env`·개인 파일(`subject/팀공유.md`) 빠졌는지 확인
- PR 본문:

```
## 한 일
## 바뀐 계약 (contracts.md) — 없음 / 있음(절 번호)
## 마이그레이션 — 없음 / 있음
## 테스트 — 실행 결과
## 리뷰어가 볼 곳
```
