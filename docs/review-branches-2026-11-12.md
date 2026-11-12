# 다른 브랜치 코드 리뷰 (2026-11-12)

- 방법: superpowers `dispatching-parallel-agents` + `requesting-code-review` 템플릿. 백엔드·프론트 리뷰 에이전트 2개를 병렬로 돌림 (읽기 전용, 임시 worktree 사용). 핵심 주장은 제가 직접 코드에서 다시 확인함 (✔ 표시)
- 범위
  - 백엔드: `origin/main`의 `backend/`
  - 프론트: `origin/frontend`의 `apps/` (main에 없는 7d·7e 커밋 3개 포함)
  - 나머지 브랜치: main에 이미 들어갔거나(backend-A-*, docs-*, frontend-auth 등), 문서·데이터만 있음(backend-B-setup, research-data, presentation)
- 실행 결과
  - 프론트: `tsc --noEmit` 오류 0, `npm run build` 성공 (번들 566kB 경고 1건). lint 스크립트·설정 없음
  - 백엔드: 이 PC 정책이 SQLAlchemy C 확장 DLL을 막아서 테스트를 못 돌림 → CI나 다른 PC에서 확인 필요

## 1. 에러가 날 수 있는 부분

### 백엔드 (main)
| 등급 | 위치 | 문제 | 수정안 |
|---|---|---|---|
| Important ✔ | `core/errors.py:19-42` | 공통 예외 핸들러 없음 → DB 오류 등은 평문 500으로 나가서 프론트가 `code`를 못 읽음 | `Exception` 핸들러 → `{code:"internal"}` 500 |
| Important ✔ | `auth/service.py:33-36` | 같은 메일로 동시에 가입하면 `IntegrityError` → 409가 아니라 500 | commit을 try/except로 감싸고 `auth.email_taken` |
| Important ✔ | `chatbot/sessions.py:22`, `ai/agent/service.py:252` 외 | 30일 보관기간 정리 함수를 운영 코드에서 부르는 곳이 없음(cron 없음) → 약속한 "30일 후 삭제"가 실제로 안 됨 | 내부 cron 엔드포인트 또는 Vercel cron |
| Important | `fx/service.py:88-99` | ECOS 장애 때 요청마다 최대 40초(10초×4통화) 대기 | 실패 시각을 기록하고 N분 동안은 저장된 값 반환 |
| Important | `ai/agent/service.py` RateLimiter | 락 없음. ai 브랜치 수정(PR #21)이 아직 main에 없음 | PR #21 머지 |
| Important | `auth/service.py:53` | 로그인 시도 제한 없음 (계약의 `auth.too_many_attempts` 미구현) | 시연 전 최소 메모리 기반 제한 |
| Minor | `fx/service.py:90-99` | 첫 호출 때 동시 요청이 오면 잘못된 503 | 실패 후 한 번 다시 읽기 |
| Minor | `chatbot/store.py:46-76` | create·append가 따로 commit해서, append가 실패하면 빈 대화가 남음 | 한 트랜잭션으로 |
| Minor | `auth/sessions.py:38-54` | 같은 파일에서 commit 규칙이 섞임 (`revoke`·`revoke_all`만 commit) | 호출자 commit으로 통일 |
| Minor | `patient/schemas.py:37` | PATCH의 `display_name` 공백이 그대로 저장됨 | `_blank_to_none` 적용 |
| Minor | `core/security.py:114-117` | 직원 토큰은 DB 확인 없이 서명만 봄 | B 직원 로그인 때 결정 |
| Minor | alembic vs 모델 | PK 이름(`patients_pkey` vs `pk_patients`), server_default 차이 | 정리용 마이그레이션 |

### 프론트 (origin/frontend)
| 등급 | 위치 | 문제 | 수정안 |
|---|---|---|---|
| **Critical** ✔ | `chatbot/useConversations.ts:18,36-44`, `components/auth.tsx:135-147` | 대화 목록이 모듈 전역 `memory['member']` 하나라서, logout·탈퇴 때 비우지 않음 → 같은 탭에서 다른 회원이 로그인하면 이전 회원의 대화가 보임. `useConsultThreads`·`useAftercare`도 같은 구조 | 사용자 id별 키 + logout·탈퇴 때 비우기 |
| Important | `useConversations.ts:111-140,171-199` | 지난 대화를 불러오는 중에 질문하면 질문과 답이 덮어써져 사라짐. 로딩 표시도 없음 | 불러오는 동안 입력 막기 + 로딩 표시 |
| Important | `useConversations.ts:138` | 네트워크 오류·503·401에도 대화를 목록에서 지움 | `not_found`일 때만 지우기 |
| Important | `auth.tsx:91-103` | 401(토큰 만료)을 공통 처리하지 않음 → 헤더는 로그인 상태인데 질문이 모두 실패 | `api()`에서 401이면 로그아웃 처리 |
| Important | `useConversations.ts:21-28` | 대화 50개 한도(429 `limit=sessions`)를 "잠시 후 다시" 문구로 안내 | 전용 문구 ("지난 대화를 지워 주세요") |
| Important ✔ | `consult/types.ts:6` | 예약 상태 코드가 계약과 다름: 프론트 `declined·completed`, 계약 `rejected·proposed·expired` | 계약 코드로 맞추기 |
| Important | `legal/aiNotice.ts:57-59`, `documents.ts:33-34` | 고지 문구("상담 내용 저장 안 함", "병원 추천·예약 안 함", "수수료 없음")가 실제 동작과 반대 | 7c 문서와 함께 갱신 |
| Important | `savedHospitals.ts:10`, `visitLog.ts:16` | 찜·방문 기록(자유 메모)을 계정 구분 없이 localStorage에 저장하고, 로그아웃·탈퇴 뒤에도 남음 | 키에 사용자 id, 탈퇴 때 삭제 |
| Minor | 여러 곳 | 입력창 maxLength 없음(백엔드 1000자) · 카드의 진료과·언어 코드가 번역 없이 보임 · `toLocaleString()` locale 없음 · 응급 고정 문구에도 `ai: true` 표시 · blob URL 누수 · 중복 SVG id · 오늘 날짜면 지난 시간 선택 가능 · 낡은 주석 2개 | — |

## 2. 불필요한 코드 (grep으로 참조 0건 확인)
| 위치 | 확신도 | 비고 |
|---|---|---|
| 5개 locale의 `header.chatbot`, `auth.comingSoon` | 높음 | 쓰는 곳 0건 |
| `styles.css:1441` `.mp-card-foot` | 높음 | 쓰는 곳 0건 |
| `features/chatbot/.gitkeep`, `backend/src/modules/auth/.gitkeep` | 높음 | 폴더에 실제 파일이 있음 |
| `ScheduleEntry.tsx:46` "더보기" 버튼 | 높음 | onClick 없음 (지우거나 기능 연결) |
| 중복 헬퍼: `uid` 4곳, `useChatText`/`shown`, `ko?ko:en` 3곳, `today`/`todayKst`, `auth.tsx` read/write vs `storage.ts` | 높음 | 합치기 권장 |
| 효과 없는 `eslint-disable` 주석 3곳 (eslint 없음) | 높음 | 지우거나 eslint 도입 |
| `features/booking-request/` 빈 폴더 | 중간 | B가 쓸 계획인지 확인 |
| `backend/src/modules/{agent,price,subscription,tenant,hospital,booking}/` (.gitkeep만) | 중간 | 특히 `agent/`는 `ai/agent/`와 겹쳐 보임 |
| `chatbot/service.py:67` `LIST_LIMIT_MAX` | 중간 | 라우터 `le=50`과 중복 |
| `auth/sessions.py:47` `revoke_all` | 중간 | 테스트에서만 씀. 비밀번호 변경용이면 유지 |
| 파일 안에서만 쓰는데 export된 타입·함수 17개 | 중간 | export 키워드만 빼기 |
| `assets/medical_illustrations_32_of_66/` 상태 파일, `apps/web-platform/README.md` 현재 상태 | 중간 | README는 갱신 대상 |

지우면 안 되는 것: `consent.service.require`, `current_staff`, `purge_*` (B 호출·cron용으로 의도됨). 백엔드에는 사용하지 않는 import가 없음.

## 3. 팀에 물어볼 것
1. **Footer에 팀원 개인 이메일**(`layout/Footer.tsx:3`)이 공개 저장소에 들어 있음 → 팀 공용 주소로 바꿀지 (CLAUDE.md 개인정보 규칙)
2. `/chatbot`이 로그인 없이도 열림 (계획 7d는 "로그인 필요"). 비회원은 미리 정한 답을 받는 하이브리드가 의도인지
3. 챗봇 카드의 `hospital_id`(데모 숫자)와 사이트 병원 id(심평원 ykiho 문자열)를 어떻게 맞출지
4. 예약 상태 코드: 프론트(`declined`, `completed`)와 계약(`rejected`, `proposed`, `expired`) 중 어느 쪽으로 맞출지
5. 고지 문구를 7c에서 누가 언제 갱신할지. 계약 4절에 `auth.invalid_credentials`·`auth.email_taken`·`chatbot.unavailable` 추가는 누가 할지
6. 메인 광고 이미지가 미용("Hanbang skincare")인데, 건강·미용 카테고리 차단 방침과 충돌하지 않는지
7. 병원 사진 1109곳이 네이버 이미지를 직접 링크함 → 공개 시연에서도 쓸지 (이용 조건 미확인)
8. 상담 화면에 "직원 온라인"이 표시되는데, 실제로는 병원이 답하지 않음 → 시연 때 실제 회원으로 보여 줄지
9. 탈퇴가 `DELETE /me` + JSON body(비밀번호) → `POST /me/withdraw`로 바꿀지
10. 동의 `version`을 아무 문자열이나 받음 → 서버가 현재 약관 버전과 맞는지 확인할지
11. `jwt_algorithm`을 env로 바꿀 수 있음 → HS256으로 고정할지
12. 챗봇 호출 제한이 실패한 호출(404·503)도 하루 150회에 셈 → 의도인지
13. 좋아요(👍) 버튼이 서버로 아무것도 보내지 않음 → 피드백을 수집할지, 장식인지
14. 대화 목록은 만든 순서로 정렬하는데 서버는 마지막 메시지 순 → 이어 쓴 대화가 아래로 묻혀도 되는지
15. `chatbot/bookings.py:20` `list_for_patient`의 `status` 인자 → B와 합의한 것인지

## 판단 보류
예약 상태 전이 race·tenant 격리(booking·hospital 모듈이 아직 없음) · 토큰을 localStorage에 보관(XSS 표면 0, 백엔드 결정 사항) · 번들 크기 · 베트남어 번역 검수 · `apps/web-hospital`(코드 없음) · 실제 브라우저·백엔드 연동 시나리오(코드만 읽고 추론함)

---

## 4. 수정 결과 (2026-11-12)

| 영역 | 브랜치 → PR | 커밋 | 확인 |
|---|---|---|---|
| 백엔드 | `backend-review-fix` → `backend` ([#22](https://github.com/k-1026/AXA/pull/22)) | 13개 | `backend/tests`+`ai/tests` **315 passed** (worktree venv에서 SQLAlchemy를 순수 Python으로 재설치해 실행) |
| 프론트 | `frontend-review-fix` → `frontend` ([#23](https://github.com/k-1026/AXA/pull/23)) | 25개 | `tsc --noEmit` 오류 0, `npm run build` 성공. 브라우저 실행은 안 함 |

- 백엔드: 1장 표의 Important 6건 모두 처리 (RateLimiter 락은 ai PR #21에서 처리). Minor 가운데 commit 규칙, display_name, 빈 세션은 고침. 마이그레이션·직원 토큰은 B 담당이라 보고만 함
- 프론트: Critical 1건, Important 7건, Minor 전부, 2장 정리 항목(높음 전부, 중간 일부) 처리. 개인정보 처리방침에 회원 계정 항목을 추가함
- 추가로 바뀐 동작: 가입 동의 terms·privacy 버전 검사, 정리 API `/internal/purge`(`CRON_SECRET`), 로그인 시도 제한, JWT HS256 고정

### 남은 팀 확인 (3장 질문 외에 새로 생긴 것)
- Vercel에서 `request.client.host`가 실제 사용자 IP인지 (프록시 IP면 IP 제한 조정 필요)
- Vercel Cron 설정(`vercel.json`)은 누가 할지, 그리고 `CRON_SECRET` 값
- 챗봇 `state` 동시 저장 충돌: 409 + 새 에러 코드로 할지, 늦은 쪽 우선으로 둘지
- 확정 예약은 환자가 취소·변경 불가 (계약대로)인 UX가 괜찮은지 · 방문 완료 상태를 백엔드에 둘지
- 법령·개인정보 문구는 초안. 정식 개정 때 `updated` 날짜와 백엔드 `CURRENT_VERSIONS`를 함께 올리기
- `docs/compliance.md` 맨 위 표의 "수수료 받기 X"가 README 4절(건당 중개수수료)과 다름 (공용 문서라 고치지 않음)
