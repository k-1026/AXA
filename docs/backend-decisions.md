# backend-decisions.md — 백엔드 결정 기록

> 정한 것은 여기 한 줄씩 (최신이 위). AI·사람 모두 **여기 있는 건 다시 논의하지 않고 따름**. 바꾸려면 새 줄로 "이전 결정 n 변경"
> 형식: 날짜 · 결정 · 이유 · 누가(A/B/팀) · 링크

| # | 날짜 | 결정 | 이유 | 누가 | 링크 |
|---|---|---|---|---|---|
| 32 | 2026-11-23 | **방문 전 질문 = 환자가 직접 보냄, 챗봇은 초안 카드만**: 예약 뒤 방문 전(`pending`·`proposed`·`confirmed`) 환자가 병원에 질문(`booking_questions`, 0013), 답은 기존 상담 답장. 챗봇 `draft_hospital_question`은 초안 카드 → 환자가 고치고 [보내기]. 의료 판단은 챗봇이 답하지 않고 병원에 묻게. 방문 뒤는 사후관리(결정 26) | AI가 환자 대신 병원에 보내지 않게(결정 26과 같음), 예약 뒤 궁금한 것을 한 흐름으로 | 사용자 (A 작성) | contracts 6-1·6-2·7 |
| 31 | 2026-11-23 | **챗봇 조건 맞춤 제안·예약 = 입점 가상 병원만, 화면 정보는 실제 대구 병원**: 가상 병원 4곳(9001~9004, `data/processed/demo/demo_hospitals.json` 한 파일)을 DB·병원 정보 화면·챗봇이 같이 씀. 챗봇 `recommend_hospitals`·`check_availability`·`prepare_booking_request`는 DB의 `is_demo` + 입점 병원만, 실제 병원은 찾기·상세만("입점 안 함" 안내). 응대 언어·시간은 지어낸 값 | 실제 병원에 가짜 제휴·예약을 붙이지 않음(compliance 2-6), 2026-11-17 결정(제안·예약은 가상 병원)을 실제 DB와 맞춤 → 시연 흐름이 끝까지 동작 | 사용자 (A 작성) | contracts 7 |
| 30 | 2026-11-23 | **웹 푸시 = 사이트 안 알림과 같은 때, 내용은 코드만**: `notify()`가 저장될 때 그 환자의 구독 브라우저에 **commit 뒤** 푸시(rollback이면 안 감). 내용은 종류·상태 코드·요청서 id·언어만, 문장은 서비스 워커가 언어별로. 구독 표 `push_subscriptions`(0012, RLS 정책 없음), 404·410이면 구독 삭제. VAPID 키 없으면 꺼짐(`push.unavailable`). 이메일은 안 함. iOS는 홈 화면에 추가한 뒤에만 | 화면을 닫아도 알림, 잠금 화면에 건강정보가 보이지 않게, 상태 변경이 취소됐는데 알림이 가지 않게 | 사용자 (A 작성) | contracts 4·6-5 |
| 28 | 2026-11-23 | **체류 형태 = 가입 때 거주국 + 3문항, 예약 요청 때 다시 확인**: ① 외국인등록(G-1 제외) ② 국내거소신고 ③ 건강보험 가입자·피부양자 — 하나라도 "예"거나 거주국 한국이면 `resident` → 정보 열람만(상담·예약 요청 403, 챗봇 조건 맞춤 제안 X). 계정 값이 챗봇 대화 값보다 우선. 기존 계정은 비어 있음 → 첫 예약 요청 전에 `PUT /me/residency`로 받음. 예약 화면 "단기 방문" 체크는 제출 때 재확인으로 유지 | compliance 2-1 계획대로, 거주자가 예약 단계에서야 막히지 않게, 체류 상태는 가입 뒤 바뀔 수 있음 | 사용자 (A 작성) | contracts 4·6·6-6 |
| 27 | 2026-11-20 | **사이트 안 알림 = 서버 알림 표 + Supabase Realtime**: 병원이 상태를 바꾸거나(확정·거절·제안·방문 완료·미방문·기간 지남) 상담·사후관리 답장을 보내면 **같은 commit**에 `notifications` 한 줄(종류·요청서 id·상태 코드만, 글·건강정보 X). 환자 웹은 백엔드가 `SUPABASE_JWT_SECRET`으로 만든 1시간 토큰으로 Realtime 구독, RLS = 자기 알림만. 읽음은 서버에. Realtime이 없으면 60초 확인. 이메일·웹 푸시는 발표 뒤 | 브라우저 비교 방식은 기기마다 다르고 서버에 기록이 없음, 예약 표 대신 알림 표만 열어 건강정보 노출 X | 사용자 (A 작성, **B 확인 필요** — booking·aftercare에 notify 줄) | contracts 5·6-5 |
| 26 | 2026-11-20 | **챗봇 사후관리 카드는 보내지 않고 연결만**: `open_aftercare_thread`는 열 수 있는지(방문 완료 + 병원 사후관리 지원)와 기존 대화 id만 확인, 카드 버튼 → 사후관리 화면에 글을 채워 두고 **환자가 직접 보냄** | AI가 환자 대신 병원에 메시지를 보내지 않게, 의료 질문 거르기는 프롬프트 규칙 그대로 | 사용자 (A 작성) | contracts 7절 |
| 25 | 2026-11-20 | **메시지 번역 = 저장할 때 `ai/llm`으로**: 환자 글 → 한국어, 직원 글 → 환자 언어 (사후관리·상담 답장·요청서 글). 그 요청서에 `overseas_transfer` 동의가 있을 때만, 보내기 전 개인정보 가림, 실패하면 원문만(보내기는 성공). 번역문은 참고용, 원문이 기준 | 동의 범위 = 요청서 글 번역(contracts 6절), 번역 실패로 상담이 막히지 않게 | 사용자 (A 작성, **B 확인 필요** — agent·booking·aftercare는 B) | contracts 6-2·6-3 |
| 24 | 2026-11-20 | **건강정보 열람 기록 `audit_logs`**: 직원이 요청서 목록·1건·사후관리 대화를 열거나 답장하면 한 줄 (누가·병원·행동·대상·시각, **내용은 저장 X**). 병원은 `GET /tenant/audit-logs`로 자기 기록만 | dashboard-integration 5-3 "건강정보 → 해당 병원 직원만, 열람 기록", 기록이 또 다른 건강정보가 되지 않게 | 사용자 (A 작성, **B 확인 필요** — audit은 B) | contracts 6-4 |
| 23 | 2026-11-20 | **사후관리 사진·영상 지우기**: 탈퇴하면 그 환자가 보낸 파일을 Storage에서 바로 삭제하고 메시지에서 경로를 뺌 (글과 "사진 있음"은 병원 쪽 기록으로 남김, 결정 15와 같음). 그 밖에 DB 메시지가 가리키지 않는 파일(보내지 않은 업로드·탈퇴 때 못 지운 것·지워진 대화)은 정기 정리(`/internal/purge`)가 **하루 뒤** 삭제 | 건강정보 최소 보관, Storage는 DB FK·CASCADE가 닿지 않음, 업로드 직후 파일을 지우지 않게 하루 여유 | 사용자 (A 작성, **B 확인 필요**) | contracts 6-3·7-1 |
| 22 | 2026-11-20 | **사후관리 사진·영상 = Supabase Storage 비공개 버킷 `aftercare-media`**. 브라우저가 서버가 준 서명된 주소로 바로 올리고(1개 50MB), 볼 때도 1시간짜리 서명된 주소만. 경로 `{tenant_id}/{request_id}/{무작위}` (원래 파일 이름 X). 설정이 없으면 "사진 있음" 표시만 | 건강정보라 공개 주소 X, Vercel 요청 크기 제한(4.5MB) 때문에 서버를 거치지 않음, DB와 같은 Supabase | 사용자 (A 작성, **B 확인 필요**) | contracts 6-3 |
| 21 | 2026-11-17 | **이전 결정 20 변경: 병원 정보 공개도 등록 병원만**. 환자에게 보이는 목록·상세·지도·챗봇 병원 찾기는 등록 유치의료기관(`is_registered_facility`, 지금 126곳)만. 미등록 병원은 목록에 없고 상세는 404 `not_found`. **DB에는 4,242곳 그대로 보관**(등록 명단이 바뀌면 적재로 `is_registered_facility`만 갱신, FK 대상 유지). 내부 함수 `get_basic()`·`require_requestable()`은 그대로. 되돌릴 땐 `hospital/service.py` `PUBLIC_REGISTERED_ONLY` 한 줄 | 복지부·진흥원 회신(2026-11-17): 외국어 병원 정보 웹도 유치거래와 결부되면 유치행위로 평가될 가능성, 대가 없어도 마찬가지 → 미등록 병원 노출이 해외진출법 제24조 제1항 제3호(미등록 기관 소개·알선 = 등록 취소 사유) 위험을 키움. 미등록 노출 가능 여부는 회신이 직접 답하지 않음 → 안전한 쪽 | 사용자(A) 요청, **팀·B 확인 필요** | contracts 4절, `docs/compliance.md` 3절 5번, `research/의료관광/등록병원-소개범위-법령확인-2026-11-16.md` 3-2절 |
| 20 | 2026-11-16 | **병원 정보는 전체, 상담·예약 요청은 등록 병원만**: (번호: B 브랜치가 18(health·404)·19(visited·no_show)를 먼저 써서 20) `GET /hospitals`·상세는 모든 병원(폐업 제외)을 주고 `is_registered_facility`·`can_request`를 표시. 요청서 제출은 `can_request = false`면 403 `hospital.not_requestable`. 정렬·노출에는 등록 여부를 반영하지 않음 | 해외진출법 제24조 제1항 제3호(미등록 기관 소개·알선 = 유치사업자 등록 취소 사유). 열람 범위는 팀이 "전체 + 등록 표시"로 결정, 복지부 질의 회신에 따라 등록 병원만으로 바꿀 수 있게 `registered` 필터를 서버에 둠 | 팀 (B 확인 필요) | contracts 4·5절, `docs/compliance.md` 2-1, `backend-A-hospital` |
| 19 | 2026-11-17 | 예약 상태에 **`visited`(방문 완료)·`no_show`(미방문)** 추가 — `confirmed`에서 병원 직원만 변경 (대시보드 명세 2-3). 환자가 병원 제안(`proposed`)을 거절하면 `cancelled` | 대시보드 방문 완료·결제 확인·사후관리가 `visited`에서 시작. 거절 전용 상태를 따로 두지 않아 흐름이 단순 | B (A 확인 필요, contracts 2절 PR 별도) | `modules/booking/service.py` |
| 17 | 2026-11-12 | 코드 리뷰 반영: 처리 못 한 예외는 500 `internal`(로그엔 예외 종류만) · 로그인·탈퇴 비밀번호 시도 제한(이메일 15분 5회, IP 15분 20회, 메모리) · JWT는 HS256 상수 고정 · 가입 동의 terms·privacy는 현재 버전만 · 정리 API `/internal/purge`(`CRON_SECRET`, 하루 1번 예약 작업이 호출) | 리뷰에서 나온 500 평문 응답·무차별 대입·보관기간 미이행 대응 | A (B 확인 필요) | `docs/review-branches-2026-11-12.md`(ai 브랜치), contracts 1·4·7-1절 |
| 16 | 2026-11-10 | **챗봇 대화 = DB 세션(최소 저장)**: `chat_sessions`(`state` jsonb 포함)·`chat_messages`에 개인정보를 가린 텍스트와 상태만 저장(도구 결과·카드 X), 30일 후 삭제·삭제 버튼·탈퇴 즉시 삭제. **이전 결정 3 일부 변경: 챗봇은 로그인 필요** (병원 찾기·상세·가격 통계는 계속 비로그인). 챗봇이 만든 요청서도 **사람이 쓰는 것과 같은 `POST /hospitals/{id}/booking-requests`** 로 제출(챗봇 전용 제출 경로 없음). 마이그레이션 `0005` | 챗봇이 대화를 이어 가고 마이페이지 "지난 대화"를 쓰려면 저장이 필요, 건강정보 저장 충돌은 입력창 고지·마스킹·짧은 보관으로 대응(스키마 5절 ⚠️, **팀 확인 필요**) | A (B 확인 필요) | [backend-db-schema.md](backend-db-schema.md) 5절, `ai` 브랜치 `docs/plan-step7-chat-api.md` |
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
| 12/4 시연 위치 | 로컬 / 호스팅 | 11/16 |
