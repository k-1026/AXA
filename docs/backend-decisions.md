# backend-decisions.md — 백엔드 결정 기록

> 정한 것은 여기 한 줄씩 (최신이 위). AI·사람 모두 **여기 있는 건 다시 논의하지 않고 따름**. 바꾸려면 새 줄로 "이전 결정 n 변경"
> 형식: 날짜 · 결정 · 이유 · 누가(A/B/팀) · 링크

| # | 날짜 | 결정 | 이유 | 누가 | 링크 |
|---|---|---|---|---|---|
| 15 | 2026-11-05 | 탈퇴 = **즉시 삭제**: 마이페이지 탈퇴 → 확인 창(비밀번호) → `patients` 행과 세션을 바로 삭제. 동의 기록은 남기고 `patient_id`만 비움. `deleted_at`·탈퇴 계정 파기 정기 작업 없음 (리비전 `0004`). 끝난 세션은 로그인할 때 정리(`purge_dead`), 배포 후엔 매일 cron 1개에서 전체 정리 | 사용자(A) 결정: 개인정보를 남기지 않음, 보관 기간을 따로 정할 필요 없음 | A (B 확인 필요) | `modules/auth/service.py` |
| 14 | 2026-11-04 | 환자 로그인 = **서버 세션 + JWT**: 로그인마다 `auth_sessions` 한 줄, 토큰 `sid`로 요청마다 확인. 로그아웃하면 `revoked_at` → 그 토큰 즉시 401. 탈퇴·비밀번호 변경 때는 모든 세션 종료(`revoke_all`) | 사용자 결정: 로그아웃하면 토큰이 바로 없어져야 함. JWT만으로는 만료(24시간) 전까지 못 막음 | A (B 확인 필요) | `modules/auth/sessions.py` |
| 13 | 2026-11-04 | **이전 결정 7 변경**: 마이그레이션 파일은 **A가 생성** (B는 모델 변경을 A에게 요청). 첫 리비전 `0001` = 환자 계정·로그인 세션·동의 | 사용자(A) 결정. 한 사람만 만들어 리비전 충돌 방지라는 이유는 그대로 | A (B 확인 필요) | `backend/alembic/` |
| 12 | 2026-11-04 | **이전 결정 2 일부 변경**: 로컬 Docker Compose 안 씀 → DB는 **Supabase PostgreSQL**(+pgvector), 배포는 **Vercel**. DB 연결은 SQLAlchemy 2 동기 + psycopg 3, `NullPool`, prepared statement 끔(트랜잭션 풀러). 테이블마다 RLS 켜고 정책 없음(Supabase 공개 API 차단) | Vercel 서버리스 배포, 팀원 PC Docker 불필요 | A (B 확인 필요) | `backend/src/core/db.py` |
| 11 | 2026-11-04 | **이전 결정 3 일부 변경**: 환자 로그인은 이메일 인증코드 대신 **이메일 + 비밀번호 회원가입** (`login_codes` 테이블 없음). 비밀번호 8~128자, argon2id 해시만 저장. 로그인 실패는 이메일 없음·비밀번호 틀림 같은 응답. 이메일은 `citext` 대신 소문자로 바꿔 `varchar(254)` | 사용자(A) 결정: 일반 회원가입으로 계정 생성. 메일 발송 없이 시연 가능 | A | `modules/auth/service.py` |
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
| `proposed` 거절 후 상태 | `rejected` / `pending` 재요청 | 11/4 |
| 메일 발송 | 콘솔 / 무료 메일 API | 12/1 |
| 요청서 보관 기간 | — | 질의 회신 후 |
| 12/9 시연 위치 | 로컬 / 호스팅 | 11/16 |
