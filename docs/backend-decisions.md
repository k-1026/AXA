# backend-decisions.md — 백엔드 결정 기록

> 정한 것은 여기 한 줄씩 (최신이 위). AI·사람 모두 **여기 있는 건 다시 논의하지 않고 따름**. 바꾸려면 새 줄로 "이전 결정 n 변경"
> 형식: 날짜 · 결정 · 이유 · 누가(A/B/팀) · 링크

| # | 날짜 | 결정 | 이유 | 누가 | 링크 |
|---|---|---|---|---|---|
| 10 | 2026-10-30 | Python 3.12 + uv(루트 `pyproject.toml`·`uv.lock`), JWT는 PyJWT(HS256), 비밀번호 해시는 pwdlib(argon2) | FastAPI 공식 튜토리얼과 같은 구성, 팀원 환경 통일(`uv sync`) | A | [FastAPI OAuth2 JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) |
| 9 | 2026-10-30 | AI 지침은 `backend/AGENTS.md` 한 곳 (Claude는 `backend/CLAUDE.md`에서 import) | Claude Code·Codex가 같은 지침을 읽게 | 팀 | [backend/AGENTS.md](../backend/AGENTS.md) |
| 8 | 2026-10-30 | 브랜치: `backend-A-*`·`backend-B-*` → `backend` PR(상대 리뷰) → `main` PR(리더 승인) | 2인 동시 작업, main 보호. `backend/A-…`처럼 슬래시를 쓰면 `backend` 브랜치와 이름이 겹쳐 Git이 만들지 못함 → 하이픈 사용 | 팀 | [backend-roles.md](backend-roles.md) 4절 |
| 7 | 2026-10-30 | 마이그레이션 파일은 B만 생성 | Alembic 리비전 충돌 방지 | 팀 | [backend-roles.md](backend-roles.md) |
| 6 | 2026-10-30 | `booking` 모델·상태 흐름 주인 = B, A는 service 함수 호출 | 같은 파일 동시 수정 방지 | 팀 | [backend-contracts.md](backend-contracts.md) 5절 |
| 5 | 2026-10-30 | 분담: A = 환자 쪽 API, B = 병원 쪽 API | 프론트와 짝, 파일 충돌 최소 | 팀 | [backend-roles.md](backend-roles.md) |
| 4 | 2026-10-30 | API 경로 `/api/v1`, 응답 값은 코드, 시간은 UTC 저장 | 프론트 i18n, 해외 환자 시간대 | 팀 | [backend-plan.md](backend-plan.md) 8절 |
| 3 | 2026-10-30 | 환자 계정(이메일 인증코드)으로 언어·시간대·동의 저장, 요청서 제출·결과 확인. 병원 정보 열람만 비로그인 | 언어 저장·결과 확인·남용 방지·동의 기록 + 공공정보 성격 유지 | 팀 | [backend-plan.md](backend-plan.md) 6절 |
| 2 | 2026-10-30 | PostgreSQL + pgvector 처음부터, 로컬은 Docker Compose | 이전 작업 없음, 챗봇 벡터 같은 DB | 팀 | [backend-plan.md](backend-plan.md) 1절 |
| 1 | 2026-10-29 | 백엔드 FastAPI (Python) | 데이터·AI와 같은 언어 | 팀 | [plan.md](../subject/plan.md) 9절 |

## 아직 안 정한 것

| 항목 | 선택지 | 언제까지 |
|---|---|---|
| 누가 A·B인지 | — (실명은 로컬 `subject/팀공유.md`에만) | 11/1 |
| 팀원 PC Docker Desktop 가능 여부 | 가능 / 공용 호스팅 DB | 11/4 |
| `proposed` 거절 후 상태 | `rejected` / `pending` 재요청 | 11/4 |
| 메일 발송 | 콘솔 / 무료 메일 API | 12/1 |
| 요청서 보관 기간 | — | 질의 회신 후 |
| 12/9 시연 위치 | 로컬 / 호스팅 | 11/16 |
