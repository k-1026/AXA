# 7단계 검증·결정·진행 계획 — 백엔드 챗봇 API 연결

> 작성 2026-11-10, 결정 반영 2026-11-10 · 대상: plan.md 12-4의 7단계
> 확인한 곳: 원격 `backend`·`frontend` 브랜치 코드와 문서, 로컬 `ai` 브랜치. 코드는 아직 쓰지 않음

## 한 줄 결론

**연결은 가능하고 방향이 정해졌다.** 대화는 **DB 세션(최소 저장)** 으로 두고, **챗봇은 로그인한 사람만** 쓰며, 제출은 **사람이 쓰는 것과 같은 예약 요청 API**를 부른다. 이 선택 때문에 **대화 테이블 마이그레이션이 필요**했고, 마이그레이션은 A 담당이라 11/10에 `0005`로 만들어 `backend-A-chatbot` 브랜치에 올렸다(`backend`에 머지하고 공용 DB에 적용하는 일이 남음). AI 쪽 서비스 층(7a)은 저장소를 바꿔 끼울 수 있게 만들어 먼저 끝냈다.

## 1. 결정 기록

| # | 결정 | 내용 | 제안(처음 안)과 달라진 점 |
|---|---|---|---|
| 1 | 7b 담당 | **내가 직접** `backend-A-chatbot`에서 만든다. `core/` 공유 파일을 고치면 PR에 표시하고 백엔드 담당 승인을 받는다 | 같음 |
| 2 | 대화 상태 | **DB 세션** (`chat_sessions`, `chat_messages`) | 서명된 상태 값을 권장했으나 DB 세션으로 결정. 마이그레이션(A 담당 — 11/10 `0005`로 완료)과 개인정보 결정이 따라옴 |
| 3 | 제출 경로 | **사람이 쓰는 것과 같은 API** `POST /hospitals/{id}/booking-requests`. 챗봇 전용 제출 경로는 만들지 않음 | 챗봇 전용 `/chatbot/submit`을 제안했으나 철회. 검증·저장 형식이 한 곳에 있어야 함 |
| 4 | 로그인 | **챗봇은 로그인 필요.** 로그인 없이는 **병원 검색(목록·지도·상세)** 만 | 계획은 "챗봇은 로그인 없이". 선택적 인증이 필요 없어져 구현은 쉬워짐 |
| 5 | 저장 범위 | **최소 저장**: 개인정보를 가린 대화 텍스트 + 체류 형태 + 요청서 초안만. 도구 호출·결과와 카드는 저장하지 않음. 초안의 `health_info`는 제출되면 지움 | — |
| 6 | `ai` → `main` PR | **7a가 끝난 뒤 한 번에** | — |
| 7 | 유료 키 전환 시점 | **미정** (시연 일정이 정해지면) | — |

### 3번을 이렇게 풀면 프론트 부담이 없다
- 요청서 카드(`booking_draft`)가 **이미 백엔드 `BookingCreate` 모양으로 변환된 값**(희망 일시는 UTC)과 `hospital_id`, `consents_required`를 담아 내보낸다
- 프론트의 [제출] = `POST /hospitals/{hospital_id}/booking-requests`에 그 값 + 환자가 체크한 동의(`kind`, `version`)를 **그대로** 보내기. 직접 쓰는 요청서 화면과 같은 호출
- 제출 뒤 대화 정리: 서버가 다음 `ask`에서 "초안의 병원에 초안 이후 만들어진 내 요청이 있는지"를 확인해 초안을 비우고 제출 사실을 대화에 반영한다. **어느 화면에서 제출했든 서버 기록이 기준**

## 2. 검증한 것 (11/10)

| 확인 | 방법 | 결과 |
|---|---|---|
| `backend`에서 `ai`를 import | `fastapi_cli` 소스, 실제 불러오기 | 가능. `fastapi dev`가 현재 폴더(저장소 루트)와 `backend/src`를 import 경로에 넣음. pytest도 같은 조건 |
| 합쳤을 때 충돌 | `git merge-tree`로 `ai`+`backend`, `ai`+`frontend` | **충돌 없음** |
| 응답 시간·호출 수·토큰 | 6턴 대화 실행(Nemotron) | 턴당 2.3~6.0초, LLM 호출 1~3회(평균 2), 입력 토큰 턴당 약 9,800 |
| 대화 기록 크기 | 같은 실행 | 6턴 뒤 약 12KB. DB 저장은 텍스트만이라 훨씬 작음 |
| 진료과 코드 | `backend-db-schema.md` | `departments.code` = 프론트 키(`dermatology`, `plastic`, `internal`, `ophthalmology`…) |
| 예약 요청 API | `backend-plan.md` | `POST /hospitals/{id}/booking-requests`(로그인, 필수 동의 없으면 422)가 이미 계획돼 있음 |
| 대화 테이블 계획 | `backend-db-schema.md` | `chat_sessions`, `chat_messages`가 **설계만** 있고 마이그레이션이 없었음(0001~0004는 환자·동의·환율·탈퇴). **11/10 `0005`가 생김** — `backend-A-chatbot` 브랜치 `7c440b3`, 아직 `backend`에 머지 전이고 공용 DB에는 미적용. "30일 후 삭제 + 삭제 버튼, 계정당 세션 수 제한"이 제안으로 적혀 있음 |
| 백엔드 테스트 실행 | `.venv` 확인 | 이 PC에서는 불가: `sqlalchemy`·`psycopg`·`alembic` 미설치 → `uv sync` 후 확인 필요 |
| 서버 직접 기동 | `fastapi.exe dev` | 실행 권한 거부, **미확인** (소스 확인으로 대체) |

## 3. 걸림돌과 처리

| # | 문제 | 처리 |
|---|---|---|
| 1 | ~~대화 테이블 마이그레이션은 B만 만든다~~ **정정**: 마이그레이션은 **A가 만든다**(`backend/AGENTS.md` 4절, 결정 13). 처음에 옛 규칙을 읽고 B에게 요청한다고 잘못 썼음 | **해결 (11/10)**: `0005`(`state jsonb` 포함)를 A가 `backend-A-chatbot`에서 작성·검증함. 남은 일: `backend` PR 머지 → 공용 DB에 `alembic upgrade head` |
| 2 | **계약과 우리 API가 다르다** (`/chatbot/ask`는 출처가 붙은 답만 정의) | 계약 수정 PR + B 승인 (7c) |
| 3 | **진료과 코드**: 챗봇은 한국어 이름(피부과 등), DB는 영어 코드. 게다가 챗봇 가상 데이터에는 치과·정형외과·한방 등 **DB에 없는 진료과**가 있음 | 도구는 한국어 이름을 받되 초안에는 `departments.code`로 변환해 넣음. 코드 표에 없는 진료과는 **병원 찾기까지만, 예약 요청 불가**로 처리(DB 진료과가 늘면 표만 확장) |
| 4 | **언어 코드**: 백엔드·프론트 5개(`ko, en, zh-TW, zh-CN, vi`), 챗봇 8개 | API 입구에서 `zh`→`zh-CN`으로 정리, 지원 밖(`ja`, `th`, `ru`)은 가장 가까운 UI 언어 + 대화 자체는 사용자 언어로 응답 |
| 5 | **LLM 설정이 실행 위치에 의존** (`env_file=".env"`) | 7a에서 파일 위치 기준 절대 경로로 수정 |
| 6 | **프론트가 카드를 못 그린다** (지금은 키워드 데모) | 7d. 카드 형식은 7a의 Pydantic 모델이 기준(OpenAPI → `packages/shared-types`) |
| 7 | **계획 문서와 어긋남**: `backend-plan.md`는 "챗봇은 로그인 없이", 프론트 `/chatbot`은 공개 | 7c·7d에서 문서와 라우트를 새 결정으로 갱신 |
| 8 | **무료 키 한도**: `gemini-3.5-flash` 하루 20회, 턴당 평균 2호출 | 로그인 필요 + 계정당 호출 제한으로 소모를 줄이고, 폴백(lite→Nemotron). 여러 사람이 쓰는 시연은 유료 키 필요 |
| 9 | **서버리스 실행 시간 제한 미확인**, 호출 제한·가짜 저장소는 인스턴스마다 따로 | 운영에서는 DB 기반 제한과 실제 `booking.service` 필요 |

## 4. 설계

### 엔드포인트 (`/api/v1`, 모두 환자 로그인 필요)
| 경로 | 하는 일 | 단계 |
|---|---|---|
| `POST /chatbot/ask` | 메시지 → 답 + 카드. `session_id`가 없으면 새 세션 | 7b |
| `DELETE /chatbot/sessions/{id}` | 대화 삭제 버튼 | 7b |
| `GET /chatbot/sessions`, `GET /chatbot/sessions/{id}` | 마이페이지 "지난 대화" 목록·내용(텍스트만) | 7e (후속) |

**`ask` 요청**: `{ session_id|null, message(1~1000자), language(5개 중 하나) }`
**`ask` 응답**: `{ session_id, text, cards[{type, data}], ai_generated, blocked, medical_notice }`
- 환자 id·시간대·언어는 **토큰과 계정에서** 가져온다(요청에 받지 않음)

### 저장 (최소 저장)
| 테이블 | 저장하는 것 | 저장하지 않는 것 |
|---|---|---|
| `chat_sessions` (+ **`state jsonb`**, 마이그레이션 `0005` 완료) | `patient_id`(탈퇴 시 CASCADE 삭제), 언어, 제목(첫 질문 앞부분, 개인정보 가림), 시각, `state` = `{residency, draft, shown_hospitals}` | 도구 결과 전체 |
| `chat_messages` | 역할(user/assistant), **개인정보를 가린** 텍스트, 거절 여부, 출처 | 카드, 도구 호출·결과 |
- 모델에게 주는 맥락 = 최근 텍스트 N개 + `state` 요약(체류 형태, 초안, "방금 보여 준 병원: 이름=id")
- 보관 **30일 후 삭제**(스키마 문서의 제안, 법적 기준은 **미확인**), 대화 삭제 버튼, 계정당 세션 수 제한, 챗봇 첫 사용 때 "대화가 저장됩니다" 고지
- **한계(솔직히)**: 개인정보 가리기는 이메일·전화·여권번호를 가릴 뿐 **증상을 쓴 문장은 그대로 저장**된다. 그래서 **요청서 초안의 `health_info`·`inquiry`는 서버에 저장하지 않는다**(허용 목록 방식, 11/10 반영). 개인정보보호위원회 질의 8번 회신 전까지는 저장 고지와 삭제 수단으로 대응하고, 회신에 따라 건강정보 동의를 추가할 수 있게 저장 층을 분리한다

### AI 쪽 서비스 층 (`ai/agent/service.py`) — FastAPI 없이 테스트됨
`ChatService.ask(patient, session_id, message, language)` → 응답. 아래 인터페이스를 주입받아 7a에서는 **메모리 구현**, 7b에서 **DB 구현**으로 바꾼다.
- `SessionStore`: 세션·메시지·상태 읽기/쓰기
- `BookingGateway`: 내 요청 목록 조회(제출 확인용), 지금은 가짜 저장소 → B의 `booking.service.list_for_patient`로 교체
- 카드 응답 모델 9종(Pydantic), 요청서 카드의 `request`(BookingCreate 모양), 언어·진료과 코드 변환, 계정당 호출 제한

## 5. 진행 순서

| 단계 | 어디서 | 내용 | 끝났다고 보는 기준 |
|---|---|---|---|
| **7a ✅ (11/10)** | `ai` | 서비스 층, 저장소·게이트웨이 인터페이스와 메모리 구현, 카드 모델, 요청서 카드의 `request` 변환, 진료과·언어 코드 변환, 제출 확인(초안 정리), `LLMSettings` 절대 경로, 계정당 호출 제한 | 이 PC에서 테스트 통과 |
| **7a-검증 ✅ (11/11)** | `ai` | 실제 모델로 6턴 시나리오를 **저장소를 거쳐**(텍스트만 저장, 도구 결과 없음) 재현. "첫 번째 병원" 같은 말을 `shown_hospitals`로 이어 가는지, 다른 계정의 세션 접근 거절 | 시나리오 10/10 유지 → 확인 항목 12개로 늘려 **12/12** (5-2절) |
| **마이그레이션 ✅ (11/10)** | `backend-A-chatbot` | A가 직접 `0005`(`chat_sessions`·`chat_messages`, RLS 켬) + 모델 + 탈퇴 시 대화 즉시 삭제 + 테스트 10개. 백엔드 테스트 88개 통과, `alembic check` 일치, 되돌리기/다시 올리기 통과, Postgres SQL 확인 | PR 머지, 공용 DB 적용 |
| **PR** | 팀 | 7a 직후 `ai` → `main` (리더 승인). 전에 공용 파일 변경(plan.md, 질의서, `pyproject.toml`, agent-spec, `.env.example`, 이 문서)을 팀에 알림 | 머지 |
| **7b** | `backend-A-chatbot` → `backend` | `uv sync` 후 기존 테스트 확인, `modules/chatbot`(모델·라우터), DB 구현 `SessionStore`, 에러 변환, 가짜 LLM 주입 테스트 | 백엔드 테스트 통과 |
| **7c** | 계약·문서 PR | `/chatbot/*` 계약, 새 에러 코드 `chatbot.unavailable`, 언어·진료과 코드, 카드 형식, 로그인 표(`backend-plan.md`)·`compliance.md`·`plan.md` 갱신 | B 승인 |
| **7d** | 프론트 | `/chatbot` 로그인 필요로 변경, API 호출로 교체, 카드 9종 표시, [제출] = 기존 예약 요청 API, 병원 검색은 로그인 없이 유지 | 브라우저 시연 |
| **7e** | 후속 | 마이페이지 "지난 대화" | — |

## 5-1. 7a 결과 (11/10)

**만든 것** — `ai/agent/`
| 파일 | 내용 |
|---|---|
| `service.py` | `ChatService.ask / delete_session / purge_expired`, 계정당 호출 제한, 입력·언어 검사, 제출 확인, 모델 맥락 복원, `ChatServiceError`(백엔드가 `AppError`로 변환) |
| `schemas.py` | 카드 9종과 `AskRequest`/`ChatResponse` (Pydantic) — 카드 형식의 기준, OpenAPI 스키마 약 11KB |
| `session_store.py` | `SessionStore` 인터페이스 + 메모리 구현(30일 정리, 탈퇴 삭제 포함). 7b에서 DB 구현으로 교체 |
| `tools/booking_store.py` | `create_from_payload`(= 사람이 쓰는 요청서 API가 하는 일을 흉내), 상태 전환 |
| 그 밖의 수정 | 언어 코드 5개로 정리(`zh`→`zh-CN`), 진료과 한국어 이름 → `departments.code`, 요청서 카드에 `hospital_id`·`request`(BookingCreate, UTC) 포함, `.env` 절대 경로 |

**검증**
- 테스트 **202개** 통과 (2026-11-10 기준. 2026-11-12 리뷰 수정 뒤 ai/tests 200개·전체 213개) (서비스 층 14개: 세션 소유, 텍스트만 저장, 호출 제한, 503, 응급, 제출 감지, 보관 기간, 카드 9종이 도구 결과와 맞는지)
- 실제 모델로 서비스 층을 거친 8턴 시나리오(저장된 텍스트만으로 이어 가고, 제출은 기존 예약 요청 API 호출로): **Gemini 10/10, Nemotron 10/10** ([결과](../ai/agent/eval/results/))
- 안전 검사 81/81, 의도 평가는 Nemotron **25~26/27** (예약 의도 2건은 실행마다 통과·실패가 바뀜 — 모델 비결정성으로 보임)

**실제로 나온 수치 (8턴, 도구 포함)**: LLM 호출 17~18회, 입력 토큰 **약 62,000(Gemini lite)~83,000(Nemotron)**, 턴당 1.4~13.6초(가장 느린 턴은 호출 3회). Gemini는 `gemini-3.5-flash` 하루 한도가 이미 찬 상태라 전부 `flash-lite`로 실행됐다

**알게 된 것 / 7b·7c에서 다룰 것**
1. **예약 요청 API에 체류 형태 칸이 없다.** `BookingCreate`(계약 6절)에는 단기 방문/국내 거주 구분이 없어서, 국내 거주자 걸러내기는 **챗봇 안에서만** 동작한다(자기 신고). 사람이 쓰는 요청서 화면에도 같은 구분이 필요하고, 서버가 확인하려면 칸(또는 계정 속성)이 필요하다 → 7c 계약 PR에 올릴 것
2. **제출 뒤 모델은 도구를 다시 부르지 않고 서버 맥락만으로 답할 수 있다.** 맥락이 정확해서 답은 맞았다(점검 항목을 "카드 또는 pending 답변"으로 고침). 대신 맥락의 상태는 감지 시점 값이라, 그 사이 병원이 확정해도 다음 질문에서 도구를 부르기 전까지는 옛 상태를 말할 수 있음
3. **국내 거주자 `resident`는 자기 신고**이고 서버 저장 상태에도 그대로 저장된다. 사용자가 처음에 거주자라고 말했다가 정정하는 경우를 처리하는 방법은 아직 없음(상태를 직접 바꾸는 경로 없음)
4. **무료 키로는 시연 한 번도 빠듯하다**: 8턴 시나리오 한 번이 약 17~18회 호출이라 `gemini-3.5-flash`(하루 20회) 한도를 한 번에 넘긴다. lite·Nemotron 폴백이 있어 지금은 통과하지만 여러 사람의 동시 시연은 불가
5. **입력 토큰**: 8턴에 6만~8만. 도구 11개의 설명이 매 호출에 들어가는 것이 큰 몫 → 유료 전환 전에 의도별로 도구를 줄이는 개선 필요

**마이그레이션 `0005` (완료, 11/10)**: `chat_sessions`(id uuid, patient_id FK CASCADE, lang CHECK 5개, title varchar(60) NOT NULL, `state jsonb` NOT NULL 기본 `{}`, created_at, last_message_at), `chat_messages`(id bigint identity, session_id FK CASCADE, role CHECK, content, refused bool, created_at). 출처 칸(`sources`)은 이번 설계에서 쓰지 않아 뺐고 스키마 문서(db-schema 5절)도 맞춰 고침. `session_store.py`의 인터페이스가 곧 DB 구현의 명세

## 5-2. 7a-검증 결과 (11/11)

확인 항목 2개를 `run_scenario.py`에 더했다(11·12번). 결과: `ai/agent/eval/results/2026-11-11-scenario-*-7a-verify.md`

| 확인 | Nemotron | Gemini |
|---|---|---|
| 1~10 기존 항목 (저장소의 텍스트만으로 이어 가기, "첫 번째 병원" → 첫 병원 id, 제출 확인, 상태 답변) | O | O |
| 11. 서버에 저장된 초안에 `health_info`·`inquiry`가 없고, 화면 카드의 `request.message`에는 문의 내용이 있다 | O | O* |
| 12. 다른 계정이 세션을 이어 쓰거나 지우면 404 `not_found`, 내 세션은 남는다 | O | O |
| LLM 호출 / 입력 토큰 | 17회 / 76,627 | 15회 / 57,371 |

\* Gemini 실행에서는 확인 코드가 칸 이름을 `inquiry`로 잘못 봐서 X로 기록됨(요청 API의 칸 이름은 `message`). 허용 밖 키는 `[]`로 저장 쪽은 문제없었고, 고친 뒤 Nemotron으로 12/12. Gemini는 하루 한도(20회) 때문에 다시 돌리지 않음

**결론**: 텍스트 + `state`만으로도 도구 결과 전체를 쓸 때와 같은 시나리오 결과가 나왔다(11/10 대비 저하 없음). 7b로 넘어가도 된다.
**확인 못 한 것**: 실제 DB(`0005`) 위의 동작은 7b에서. 여러 번 반복 실행한 통계는 없음(모델마다 1회).

## 6. 남은 결정
1. 유료 키 전환 시점 (시연 일정에 따라)
2. 보관 기간 30일 확정 여부 (현재는 스키마 문서의 제안)
3. 예약 요청이 가능한 진료과 범위: DB의 4개(피부·성형·내과·안과)만으로 시작할지, DB를 넓힐지
4. 개인정보보호위원회 질의 8번 회신에 따른 건강정보 동의 추가 여부

## 7. 위험
- **`0005`가 `backend` 브랜치에 머지되기 전에는 DB 구현을 공용 DB에서 시험할 수 없다.** 완화: 테스트는 메모리 SQLite라 머지와 무관하게 진행 가능, 공용 DB 적용은 PR 머지 뒤
- 텍스트와 `state`만으로 대화를 이어 가는 것이 도구 결과 전체를 쓸 때보다 약해질 수 있음 → 7a-검증에서 확인: 시나리오 12/12, 저하 없음(모델마다 1회 실행)
- 입력 토큰이 큼(턴당 약 9,800): 도구 설명 11개가 매 호출에 들어감. 유료 전환 시 비용이므로 의도별로 도구를 줄이는 개선 필요
- 로그인 필요로 바뀌면 처음 방문자가 챗봇을 못 써 보고 이탈할 수 있음(제품 판단)
- 프론트 작업이 늦으면 API가 완성돼도 시연 화면이 안 나옴

## 출처

| 이름 | 위치 | 등급 | 기준 시점 | 확인일 |
|---|---|---|---|---|
| 백엔드 진입점·설정·인증·에러·모델·테스트 설정 | `origin/backend`: `backend/src/main.py`, `core/config.py`, `core/security.py`, `core/errors.py`, `modules/patient/*`, `tests/conftest.py`, `pyproject.toml` | 개인(팀 코드) | 2026-11-05 (`f1f1f8f`) | 2026-11-10 |
| 계약·계획·DB 스키마·분담·작업 일지 | `origin/backend`: `docs/backend-contracts.md`, `backend-plan.md`, `backend-db-schema.md`, `backend-todo-A.md`, `backend-worklog-A.md` | 개인(팀 문서) | 2026-11-05 | 2026-11-10 |
| 프론트 챗봇·API 헬퍼·라우트·언어 파일 | `origin/frontend`: `features/chatbot/*`, `components/api.ts`, `main.tsx`, `i18n/locales/` | 개인(팀 코드) | 2026-11-09 (`d05f9be`) | 2026-11-10 |
| `fastapi dev`의 import 경로 | 설치된 `fastapi_cli/discover.py` 소스 | 공식(라이브러리 소스) | 설치 버전 | 2026-11-10 |
| 병합 충돌 미리 보기 | `git merge-tree --write-tree origin/backend HEAD`, `origin/frontend HEAD` | 개인(실행 결과) | 2026-11-10 | 2026-11-10 |
| 응답 시간·호출 수·토큰·기록 크기 | 6턴 대화 실행(Nemotron, 가상 데이터) | 개인(실행 결과) | 2026-11-10 | 2026-11-10 |
| Gemini 무료 하루 한도 20회 | Google AI Studio 429 응답의 `quotaValue` | 공식(API 응답) | 2026-11-10 | 2026-11-10 |
| 결정 7건 | 팀원 답변(대화) | 개인 | 2026-11-10 | 2026-11-10 |
