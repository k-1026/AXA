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

### 2026-11-27 · backend-A-translate-retry · Claude (번역 실패는 다시 시도)
- 한 일: **B 파일 `agent/translate.py`·`booking/router_tenant.py`·`booking/schemas.py` 수정 (사용자 지시)** — `translate()`가 실패·빈 답이면 0.6초 뒤 한 번 더. `retry_missing()`: 최근 30일 요청서 글·방문 전 질문·병원 답장·사후관리 글 중 번역이 빠지고 동의가 있는 것을 다시 번역. 직원 `POST /tenant/translations/retry`(최대 10), 정리 `/internal/translations`(최대 50, GitHub Actions 1시간마다 — reminders.yml에 한 단계). 병원 예약 응답에 `translation_allowed` → 대시보드가 "동의 없음"과 "번역 실패(다시 시도)"를 나눠 보임
- 바뀐 계약: contracts 변경 이력 1줄
- 테스트: 백엔드 338개 통과 (새 4개: 그 자리 재시도·두 번 실패·나중에 다시 번역(동의 있는 것만)·정리 작업 비밀값)
- 다음 할 일: 대시보드 표시 (`frontend-translate-retry`)
- B에게 요청: 확인
- 막힌 것·질문: 없음
### 2026-11-27 · backend-A-views-daily · Claude (홈 방문자 일별 카드)
- 한 일: **B 파일 `booking/analytics.py`·`router_tenant.py` 수정 (사용자 지시)** — `series`에 `daily=true`(하루 = 한 점, 최대 62일, 넘으면 422). 홈 "방문자 수 — 이번 달 vs 지난 기간 (일별)" 카드가 예시값 대신 이 값
- 테스트: 백엔드 335개 통과 (새 1개)
- 다음 할 일: 없음
### 2026-11-27 · backend-A-paid · Claude (요청부터 결제까지 확인)
- 한 일: **B 파일 `booking/models.py`·`service.py`·`schemas.py`·`router_tenant.py` 수정 (사용자 지시)** — 상태 `paid` + `visited → paid` 병원 행동(금액·수단 필수), `paid_amount`·`paid_method` 칸(마이그레이션 0018, 상태 CHECK 2곳 다시 만듦). 알림 상태 `paid`, 사후관리·챗봇 예약 요약은 `paid`도 방문 완료로 봄. 단계별 시연 스크립트 `backend/scripts/seed_flow_demo.py` (가상 환자 6명: 대기·시간 제안·확정·방문 완료·결제 확인 2, `--remove`로만 지움, SQLite로 두 번 돌려 같은 결과 확인)
- 바뀐 계약: contracts 2절·변경 이력, 결정 38
- 테스트: 백엔드 343개 통과 (새 9개: 결제 확인 흐름·알림, visited에서만, 금액·수단 검증, 다른 행동에 금액 X, API·목록)
- 다음 할 일: 공용 DB 0018 적용(사용자 확인 후) → 시연 스크립트 실행, 대시보드 "진료·결제 확인" 탭·환자 화면 연결 (`frontend-paid`)
- B에게 요청: 상태 흐름 변경 확인
- 막힌 것·질문: 환자 금액 확인·이의 제기·영수증 파일은 아직 없음

### 2026-11-27 · backend-A-page-views · Claude (요청 1번: 방문자 수 = 상세 페이지 조회)
- 한 일: 새 모듈 `modules/pageview` (`page_events` 테이블, 마이그레이션 0017 — 0016 다음이라 `backend-A-staff-realtime` 위에 만들고 `backend-A-analytics-series`를 합침). `POST /hospitals/page-views` 로그인 없이, 같은 병원·방문자·한국 날짜는 한 줄. **B 파일 `booking/analytics.py` 수정 (사용자 지시)** — `summary`·`series`의 `views` = 기간 안 줄 수(날마다 다른 방문자 수의 합), 지난 기간도
- 바뀐 계약: contracts 변경 이력 1줄, 결정 37
- 테스트: 백엔드 330개 통과 (새 4개: 하루 한 번만 셈·개인정보 칸 없음·API 검증·대시보드 숫자는 내 병원만+지난 기간+series)
- 다음 할 일: 공용 DB에 0017 적용 (사용자 확인 후), 프론트 상세 페이지에서 보내기·대시보드 그래프 (`frontend-page-views`)
- B에게 요청: `analytics.summary`·`series` 변경 확인
- 막힌 것·질문: 보관 기간(제안 13개월) 미정, 요청 횟수 제한 없음(같은 날 같은 값은 한 줄이라 숫자는 안 부풀지만 다른 값을 계속 보내면 늘어남)

### 2026-11-27 · backend-A-analytics-series · Claude (대시보드 첫 화면 느림)
- 한 일: **B 파일 `booking/analytics.py`·`router_tenant.py` 수정 (사용자 지시: "그냥 너가 하고 올리면")** — `GET /tenant/analytics/series?from&to` 추가. 홈 "기간 성과" 그래프가 구간마다 summary를 따로 불러 처음 접속 때 19번(로컬 측정 그래프까지 6.3초) → 1번. 조회 2번(요청 생성 시각, 확정·취소·방문 이벤트 시각)을 한국 날짜로 나눠 구간 합. 구간 크기 = ceil(일수/12), 지난 기간은 같은 길이 바로 앞 기간을 같은 위치로. 최대 366일(넘으면 422). summary는 그대로
- 바뀐 계약: contracts 변경 이력 1줄 (6-2 병원 API 추가), `dashboard-integration.md` 표 1줄
- 테스트: 백엔드 323개 통과 (새 2개: 구간 숫자 = 그 구간 summary의 now·prev, 한국 날짜 경계, 직원만·기간 제한)
- 다음 할 일: 프론트 `KpiTrends`가 series 사용 (`frontend-dashboard-load`)
- B에게 요청: `analytics.series` 확인 (summary 계산과 같은 기준인지)
### 2026-11-27 · backend-A-residency-nationality · Claude (국적 한국 → 국내 거주 취급)
- 한 일: `ResidencyIn.nationality?` (KR → resident, 저장 안 함), 예약 요청서 국적 KR → 403 `residency.not_eligible`(`korean_nationality`), 챗봇 `prepare_booking_request` 국적 KR → not_available (결정 36)
- 바뀐 계약: contracts 6-1·6-6·7 (칸 추가만)
- 테스트: backend 324 passed (test_residency 3개 추가), AI 244 passed (1개 추가)
- 다음 할 일: 화면 가입·마이페이지에 국적 질문 (frontend PR)
- B에게 요청: 없음
- 막힌 것·질문: 재외국민이 법적으로 외국인환자인지 미확인 — 규제 담당 확인 필요
### 2026-11-27 · backend-A-staff-realtime · Claude (병원 대시보드 실시간 알림)
- 한 일: `staff_notifications` 표(0016, RLS·Realtime) · `notify_staff()` · `POST /tenant/notifications/realtime-token`. 환자 요청 생성·취소·수락·질문·사후관리 글에서 병원에 한 줄 (결정 35)
- 바뀐 계약: contracts 5·6-5
- 테스트: backend 324 passed (새 테스트 `test_staff_notifications.py` 3개)
- 다음 할 일: 공용 DB에 0015(리마인드, #122)·0016 적용 — **공용 DB가 아직 0014라 main의 리마인드 알림(kind=reminder)이 CHECK에 걸림**
- B에게 요청: `booking/service.py`의 `create_request`·`_move`에 `notify_staff()` 한 줄씩 넣음 — 확인 부탁
- 막힌 것·질문: 없음

### 2026-11-25 · backend-A-contract-signup-closed · backend-A-signup-guard · Claude (입점 신청 막기, 전체 점검 N1)
- 한 일: 직원 가입(`auth/staff.py` signup)이 등록번호 확인·운영자 승인 없이 실제 병원 owner를 만들고 `requests_enabled=True` → 누구나 실제 병원 160곳 중 아무 데나 먼저 가입해 그 병원 환자 요청서를 받을 수 있었음. 이제 가상 병원(`is_demo`)만 가입, 실제 병원은 403 `auth.signup_closed`(계정 안 만듦). 설정 `staff_signup_real_hospitals`(env `STAFF_SIGNUP_REAL_HOSPITALS`, 기본 false) — **`core/config.py` 공통 파일 변경**. 테스트 conftest에서 false 고정. 앞서 `backend-A-request-hours`(PR #106): 환자 희망 일시도 진료시간 안만(422 `closed`, loc `preferred_slots[i]`) + 챗봇 초안 단계 검사
- 바뀐 계약: contracts 3·4절 (`auth.signup_closed` 403), 변경 이력 1줄, 결정 34
- 테스트: 백엔드·AI 523개 통과 (새 3개, `backend` 기준 — #106 제외)
- 다음 할 일: 프론트 가입 화면에 `auth.signup_closed` 문구(6개 언어, 지금은 "알 수 없는 오류"로 보임). 실제 병원 입점 절차(등록번호 확인·운영자 승인)는 12/4 뒤
- B에게 요청: `core/config.py` 변경·contracts 4절 새 코드 확인
- 막힌 것·질문: 없음

### 2026-11-24 (2) · backend-A-vercel-cron · Claude (결정 33 — 제안 시간은 환자 수락만, 진료시간 안만)
- 한 일: **B 파일 `booking/service.py` 수정 (사용자 지시: "B한테 넘기지 말고")** — TRANSITIONS에서 `("proposed", "confirm")` 제거, `staff_act`의 propose에 `_check_open`(그 병원 `hospital_hours`, 한국 시간, 휴진·진료 전후·점심이면 422 validation, 데이터 없으면 통과). 알림 테스트를 "제안 → 환자 수락"으로 바꿈
- 바뀐 계약: contracts 2절 (상태 표), 변경 이력 1줄, 결정 33
- 테스트: 백엔드·AI 516개 통과 (새 8개)
- 다음 할 일: 제안 기한(환자가 수락 안 하면 만료) — 추후. 대시보드 "제안 보기"에서 병원 확정 버튼 제거·제안 창 진료시간 필터 (`frontend-dashboard-district`)
- B에게 요청: 결정 33·`booking/service.py` 수정분 확인 (A가 고친 B 파일)
- 막힌 것·질문: 없음

### 2026-11-24 · backend-A-visa-quote · backend-A-llm-log · backend-A-chatbot-early-check · backend-A-vercel-cron · Claude (Vercel 첫 배포·챗봇 점검)
- 한 일: Vercel 첫 배포(백엔드 `axa` sin1 · 환자 웹 `axa-tqse`, `docs/deploy-vercel.md` 0절). 배포본 시연 흐름·금지 요청 11개 확인 (로컬 `docs/시나리오.md`).
  #95 LLM 호출마다 `llm ok|fail … model ms tokens fallback_from` 로그. #94 요청서 `visa_needed`는 사용자 말(`visa_statement`)이 대화에 있을 때만 + 비자 자격·절차 질문은 "계신 나라의 한국 대사관·영사관" 안내(의료 고지 X, 비자 문서 미반환).
  `backend-A-chatbot-early-check`: 병원을 고르면 `prepare_booking_request` 먼저(요청 불가면 첫 턴에 안내), not_available 전화번호에 053, DB 연결 시 가짜 가격 대신 가격 가이드 안내, 병원 id 숨김·상담 언어 묻기.
  루트 `vercel.json` Cron 2개 — 환율 미리 받기(`/api/v1/exchange-rates`)·정기 정리(`/api/v1/internal/purge`) 둘 다 매일 한국 10시(UTC 01시)
- 바뀐 계약: 없음 (챗봇 도구 입력에 `visa_statement` 추가 — 챗봇 내부)
- 테스트: 백엔드·AI 511개 통과 (early-check 기준)
- 다음 할 일: #97(backend→main) 승인·머지 뒤 배포본에서 비자·요청 흐름 재확인. 시연 때 `LLM_PROVIDER_ORDER`(지금 nemotron,gemini) 결정. 챗봇 가격을 가격 가이드 데이터에 연결
- B에게 요청: 없음 (대시보드 머리말 지역·번역 줄은 프론트 `legacy.js`에서 처리)
- 막힌 것·질문: ⚠ 규칙 위반 2건 — ① `backend`를 main으로 **직접 fast-forward push**(111커밋 뒤처져 PR에 무관한 커밋이 섞여서, 사용자 승인 후). 지운 커밋 없음. ② #94·#95·#97 PR 본문이 8절 양식이 아님. 다음부터 지킴

### 2026-11-23 (2) · backend-A-media-thumbs · Claude (사진 썸네일)
- 한 일: 결정 29. `media.thumb_path`·`with_thumbs`, 업로드 `thumb?` → `thumb_upload_url`, 첨부 `thumb`, `attachments_out`에 `thumb_url`. 탈퇴 삭제·정기 정리에 썸네일 포함
- 바뀐 계약: contracts 6-3 (칸 추가만)
- 테스트: 전체 456개 통과 (새 4개)
- 다음 할 일: 환자 웹 업로드 전 줄이기·썸네일 (`frontend-media-thumbs`), 대시보드 썸네일 표시
- B에게 요청: 결정 29 확인 — `router_tenant` 응답 첨부에 `thumb_url`이 생김 (B 파일은 안 고침, `media.attachments_out`이 같이 줌)
- 막힌 것·질문: 없음
### 2026-11-23 (4) · backend-A-chatbot-demo-flow · Claude (챗봇 가상 병원 흐름 + 방문 전 질문, `backend-A-web-push` 위)
- 한 일: 결정 31·32. 가상 병원 4곳 `demo_hospitals.json`(예전 `demo_hospital.json` 대신), 시드가 4곳·병원별 직원 계정. 챗봇 게이트웨이 `demo_candidates`·`booking_info`(입점 가상 병원만), `recommend_hospitals`·`check_availability`·`prepare_booking_request`가 서버에서는 DB 사용(테스트는 가상 데이터 그대로). 새 모듈 `question`(마이그레이션 **0013**), `POST /me/booking-requests/{id}/questions`, 응답 `questions`, 챗봇 도구 `draft_hospital_question` + 카드 `hospital_question`
- 바뀐 계약: contracts 6-1·6-2·7
- 테스트: 전체 484개 통과 (새 `test_questions.py` 5개, `test_chatbot_hospitals.py` 3개, 도구 12개)
- 다음 할 일: 공용 DB 0013 + 시드 다시, 환자 웹 카드·상담 화면, 대시보드에 질문 표시
- B에게 요청: `booking/router_tenant.py`·`schemas.py`에 `questions` 칸 (A 작성, 확인 부탁)
- 막힌 것·질문: AI 담당 확인 — 도구 1개·프롬프트 한 절("Questions before the visit")·서버에서 DB 쓰는 분기

### 2026-11-23 (3) · backend-A-web-push · Claude (웹 푸시, `backend-A-residency` 위)
- 한 일: 결정 30. `pywebpush` 의존성, 설정 `VAPID_*`, 모델 `PushSubscription`(마이그레이션 **0012**), `notification/push.py`(구독·해제·commit 뒤 보내기·410 정리), API `/me/push/key`·`/me/push/subscriptions`, 키 생성 `scripts/make_vapid_keys.py`. `notify()`에 한 줄(`push.queue`)
- 바뀐 계약: contracts 4·6-5
- 테스트: 전체 통과 (새 `test_push.py` 8개 — 실제 pywebpush 암호화·서명 포함, 네트워크는 가짜)
- 다음 할 일: 환자 웹 서비스 워커·구독 버튼 (`frontend-web-push`), 공용 DB 0012, 배포 때 Vercel에 `VAPID_*`
- B에게 요청: 결정 30 확인 — B 코드는 안 고침 (notify 호출 그대로, commit 뒤 푸시)
- 막힌 것·질문: `VAPID_SUBJECT` 운영 연락 주소는 팀이 정함

### 2026-11-23 · backend-A-residency · Claude (체류 형태 가입 때 묻기)
- 한 일: 결정 28. `patients`에 `residency`·`residence_country`·`residency_answered_at` (마이그레이션 **0011**, 칸 추가만), 가입 `residency?`(3문항 + 거주국), `PUT /me/residency`, `PatientOut` 칸 추가. 예약 요청 전 `patient.service.require_short_term()` (없으면 422 `residency.required`, 국내 거주 403 `residency.not_eligible`). 챗봇 `PatientInfo.residency` → 계정 값 우선·`record_residency`가 못 바꿈 (`ai/agent` 3줄: `residency_locked`)
- 바뀐 계약: contracts 4·6·6-1·6-6
- 테스트: 전체 467개 통과 (새 `test_residency.py` 13개, `ai/tests/test_service.py` 2개, `test_booking_patient` 가입에 3문항 추가)
- 다음 할 일: 공용 DB 0011 적용, 시연 환자 계정 `short_term`으로, 프론트 가입·예약 화면 (`frontend-residency`)
- B에게 요청: 결정 28·contracts 6-6 확인 (예약 요청 앞에서 막음 — booking 서비스는 안 고침)
- 막힌 것·질문: AI 담당 확인 — `ai/agent` `residency_locked` (ToolContext·ConversationState 칸 1개씩, `record_residency` 첫 줄)

### 2026-11-20 (5) · backend-A-notifications · Claude (사이트 안 알림)
- 브랜치: `backend-A-audit-translate` 위 → 그것이 먼저 머지돼야 함
- 한 일: 결정 27. 새 모듈 `modules/notification/`(A) — 모델·`notify`·목록·읽음·Realtime 토큰(PyJWT HS256, `SUPABASE_JWT_SECRET`), 마이그레이션 **0010** (표 + Supabase에서만 RLS 정책·authenticated SELECT·Realtime 발행). `booking/service._move`·`staff_reply`, `aftercare/service.tenant_reply`에 `notify` 한 줄 (B 모듈). `core/config.py`에 `supabase_jwt_secret` (공통 파일). `.env.example` 정리 (CORS·Supabase 묶음)
- 바뀐 계약: contracts 4·5·6-5
- 테스트: 전체 452개 통과 (`conftest`에서 `SUPABASE_JWT_SECRET` 비움)
- Supabase `AXA`: 0010 적용, 정책 `notifications_own`·Realtime 발행 확인
- B에게 요청: booking·aftercare에 넣은 `notify` 줄, `core/config.py` 확인

### 2026-11-19 · backend-A-demo-seed · Claude (시연용 가상 병원 공용 DB 시드)
- 한 일: `backend/scripts/seed_demo_shared.py` — 시연은 **가상 병원 9001**로 (사용자 결정, compliance 2-6: 예시 일정·예약은 `is_demo` 병원에만). 공용 DB에 여러 번 돌려도 같은 결과
  - 9001 이름·가상 주소·좌표·진료시간·진료과를 `data/processed/demo/demo_hospital.json`(환자 웹 목록과 같이 읽을 파일)로 채움, `is_registered_facility = true`(요청 흐름용) · `is_demo = true`
  - 9001 tenant 요청·사후관리 켬, 직원 `demo-staff@example.com`(owner), 환자 `demo-patient@example.com` + 그 환자 예약 2건(방문 완료·확정, 동의·이벤트 포함 — 대기는 넣지 않음: 있으면 시연 중 새 요청이 409 `booking.duplicate`). 다시 돌리면 이 환자 예약만 새로 만듦
  - 비밀번호는 처음 만들 때만 생성 → `data/dev/demo_accounts.txt`(git 제외), `--reset-passwords`로 새로
  - B 시드(`seed_demo.py`, 로컬 SQLite)와 9001 대시보드 데이터(환자 없는 요청 167건)는 그대로
  - 이메일은 `example.com` — `.test`는 `EmailStr`이 거부(로그인 422)
- 확인 (로컬 SQLite, 새 DB에 3번 실행): 예약 3·이벤트 6·동의 5 그대로(대기 포함 버전), 환자 로그인 200 → `/me/booking-requests` 3건. Supabase 실행 후 브라우저로 요청 → 대시보드 확정 → 환자 예약 관리 "확정"·예약번호까지 확인, 직원 로그인 200 → `/tenant/booking-requests` 200, `/hospitals/9001` `is_demo`·`can_request` true
- 바뀐 계약: 없음
- 테스트: pytest는 이 PC에서 실행 불가 → 위 수동 확인만
- 다음 할 일: 병원 재적재(등록 126 → 160) 끝난 뒤 Supabase에 실행, 환자 웹 목록에 9001 "가상 · 시연용"으로 표시(프론트 브랜치)
- B에게 요청: 대시보드 시연은 `demo-staff@example.com`으로 로그인 (`?token=` 대신). 기존 `coordinator@demo.test`는 비밀번호 해시가 없어 로그인 불가 — 그대로 둠
### 2026-11-20 (4) · backend-A-audit-translate · Claude (열람 기록 · 번역 · 챗봇 사후관리 카드)
- 브랜치: `backend-A-aftercare-patient` + `backend-A-booking-replies` + `backend-A-chatbot-bookings`를 합친 위 → **그 셋이 먼저 머지돼야 함**
- 한 일
  - 결정 24 열람 기록: 새 모듈 `modules/audit/`(B 모듈) 모델·`log_action`·`GET /tenant/audit-logs`, 마이그레이션 **0009**. 병원 요청서 목록·1건·답장, 사후관리 열람·답장에서 기록
  - 결정 25 번역: `modules/agent/translate.py`(B 모듈) — `ai/llm` 클라이언트, `mask_pii`, 동의 확인(`consent.given_for_request` 추가). 사후관리 환자·직원 글, 상담 답장, 요청서 글(저장 뒤)
  - 결정 26 챗봇: `open_aftercare_thread`가 `BookingGateway.aftercare_for()`로 실제 가능 여부·대화 id 확인, 카드에 `booking_id`, 보내지 않음. 프롬프트 한 줄 (`ai/agent` — AI 담당 확인)
- 테스트: 전체 443개 통과 (`conftest`에서 번역 LLM 끔 — 실제 LLM 안 부름)
- B에게 요청: `audit/`·`agent/translate.py`·`booking/service.staff_reply`·`aftercare/service` 번역 줄·`router_tenant` 기록 줄 확인
- 다음: Supabase에 0009 적용, 환자 웹 챗봇 카드·자기 글 원문 표시

### 2026-11-20 (3) · backend-A-aftercare-patient · Claude (사진·영상 지우기)
- 한 일: 결정 23. 탈퇴(`auth.service.withdraw`)에서 `aftercare.detach_patient_media()` → commit 뒤 `media.remove()`. 정기 정리 `maintenance.purge_media()` — Storage 목록(`media.list_objects`) 중 DB가 가리키지 않는 하루 지난 파일 삭제, Storage 오류여도 다른 정리는 끝남. 테스트 `conftest.py`에서 `SUPABASE_*`를 비움 (.env에 키가 있어도 실제 Storage를 부르지 않게)
- B 모듈 변경 (**B 확인 필요**): `aftercare/service.py`에 `detach_patient_media`·`referenced_media_paths`
- 바뀐 계약: contracts 6-3·7-1 (`media_files`)
- 테스트: 전체 224개 통과
- 다음 할 일: Vercel Cron에 `/internal/purge` 등록 (배포 때)

### 2026-11-20 (2) · backend-A-aftercare-patient · Claude (사후관리 사진·영상 = Supabase Storage)
- 한 일: 결정 22. 새 모듈 `modules/media/`(A) — 서명된 업로드·보기 주소 (httpx, 서비스 키는 서버만). `POST /me/booking-requests/{id}/aftercare/uploads`, 보내기에 `attachments`, 환자·병원 메시지 응답에 `attachments[{kind, name, url}]`. 마이그레이션 **0008** (`aftercare_messages.attachments`). 버킷 만들기 `backend/scripts/setup_storage.py`
- 공통 파일 변경: `core/config.py`에 `supabase_url`·`supabase_service_role_key` (**B 승인 필요**), `.env.example`
- B 모듈 변경 (**B 확인 필요**): `aftercare/models.py` 칸 1개, `service.py` `_openable`·`media_prefix`·`patient_upload_prefix` + `_add(attachments)`, `router_tenant.py` 메시지에 `attachments`
- 바뀐 계약: contracts 4절(`storage.unavailable`)·6-3
- 테스트: 전체 218개 통과 (업로드·보기 주소, 다른 요청서 파일 422, 파일 종류·크기·권한, 설정 없음 503, Supabase 응답 처리)
- 다음 할 일: `.env`에 키 → `setup_storage.py` → Supabase에 0008 적용 → 환자 웹·대시보드 연결 확인
- 막힌 것·질문: 탈퇴·대화 삭제 때 Storage 파일도 지우기는 아직 (DB 행만 지워짐) → 정리 API(`maintenance`)에 추가 필요

### 2026-11-20 · backend-A-aftercare-patient · Claude
- 한 일: 환자 사후관리 API 3개 (`GET /me/aftercare`, `GET·POST /me/booking-requests/{id}/aftercare[/messages]`). 새 파일 `aftercare/router_patient.py`(A), `aftercare/service.py`에 조회 함수 `patient_list`·`patient_messages` 추가 (B 모듈 — 확인 요청), `main.py`에 라우터 등록
- 바뀐 계약: contracts 6-3 신설
- 테스트: 전체 210개 통과 (새 `test_aftercare_patient.py` 5개: 열기·답장 안 읽은 수, 409, 남의 것 404, 빈 글 422, 401·403)
- 다음 할 일: 환자 웹 사후관리 화면을 이 API로 (회원 모드)
- B에게 요청: `aftercare/service.py` 추가 함수 2개와 6-3절 확인. 사진 저장 방식(스토리지) 정하기
- 막힌 것·질문: 없음

### 2026-11-20 · backend-A-booking-replies · Claude (병원 상담 답장 API)
- 한 일: 사용자 요청으로 **B 모듈(booking)에 상담 답장 쓰기 API** — 대시보드 상담 답장이 화면에만 붙고 새로고침하면 사라지던 것
  - `POST /tenant/booking-requests/{id}/replies` `{text}` → `Reply` 저장 (`sent_at` 지금, `approved_by` = 보낸 직원, `ai_draft` false, 번역 비움). 확인 창 "보내기" = 직원 승인
  - 병원 목록·상세 응답 `TenantBookingOut` = `BookingOut` + `replies` (한 번에 조회, `service.sent_replies`)
  - `/replies` 경로를 `/{action}`보다 먼저 등록 (행동 이름으로 잡히지 않게)
  - 환자 쪽 `_out()`이 답장을 dict로 넣어 Pydantic 경고 → `ReplyOut`으로 (답장이 실제로 생기면서 드러남)
- 바뀐 계약: 있음 6-2절 신설 + 변경 이력 (**B 확인 필요**)
- 테스트: `backend/tests/test_booking_replies.py` 5개 (저장·병원/환자 조회, 다른 병원 404, 빈 글·2,001자 422, 로그인·환자 토큰 막기, 경로 충돌 없음), 백엔드+AI 410개 통과
- 다음 할 일: 대시보드 상담 채팅이 이 API로 보내고 불러오기, 환자 웹 상담 화면에 답장 표시 (프론트 브랜치)
- B에게 요청: 6-2절·`staff_reply()` 확인. 상태 이력(`booking_events`)에는 답장을 넣지 않음 — 넣어야 하면 알려 주기
- 막힌 것·질문: 번역은 `ai/llm` 연결 후 (`text_translated`)

### 2026-11-19 (2) · backend-A-chatbot-bookings · Claude (챗봇 "내 예약" 연결)
- 한 일: `modules/chatbot/bookings.py` 빈 목록 → `booking.service.list_for_patient`·`get_for_patient`(계약 5절) 어댑터
  - 챗봇 도구 모양 그대로: `id`·`hospital_id`·`hospital_name_en`·`status`·`preferred`·`confirmed_slot`·`proposed_slot`·`created_at`·`visited`, 시간은 한국 시간 "YYYY-MM-DD HH:MM"
  - `confirmed_slot` 칸(확정·제안 시간 같이 담음)을 상태로 나눔: proposed → `proposed_slot`, confirmed·visited·no_show → `confirmed_slot`
  - 요청서 원문·건강정보·동의·답장은 넘기지 않음, 남의 요청·UUID 아닌 id는 `BookingError("not_found")`
  - 이걸로 챗봇 "제출 확인"(초안 병원에 새 요청이 생기면 제출로 봄)도 실제 DB 기준으로 동작
- 확인: Supabase + 시연 환자로 "내 예약 상태 알려줘" → 9001 예약 3건 상태(확정·미방문·방문 완료)로 답함 (확인용 대화는 지움)
- 바뀐 계약: 없음
- 테스트: `backend/tests/test_chatbot_bookings.py` 3개 추가, 백엔드+AI 408개 통과 (**이 PC에서도 pytest 실행됨** — 11/18 메모의 "실행 불가"는 지금은 아님)
- 다음 할 일: 없음 (사후관리 열기 `open_aftercare_thread`는 아직 데모 응답 — 환자 사후관리 API 생기면)
- B에게 요청: 없음


### 2026-11-17 (7) · backend-A-migration-0007 · Claude (Supabase 0007 적용)
- 한 일: 사용자 요청으로 **#29 머지 전에 Supabase `AXA`(`afypgiqkrohgoybqhtsi`)에 `0007` 적용** (이 PC, PostgreSQL 18 libpq). `medi`는 **미적용**
- 확인: alembic `0007` · hospitals 4,242(등록 126) 그대로 · 새 표 7개 모두 0행 · public 표 RLS 꺼진 것 0 · FK `tenants·booking_requests.hospital_id → hospitals`, `consents.booking_request_id → booking_requests` 있음
- 서버(0007 브랜치, Supabase)로 확인: health 200, 직원 토큰(가짜 tenant)으로 `/tenant/booking-requests`·`/tenant/aftercare` 200 `[]`, `/tenant/analytics/summary` 200 → 표가 있어 500 안 남. `/tenant/me`는 직원 행이 없어 401
- ⚠️ #29 리뷰에서 0007이 바뀌면 `downgrade 0006` 후 다시 `upgrade head` (지금 새 표는 비어 있음). 시연 데이터를 넣을 땐 실제 병원에 가짜 병원 계정을 붙이지 말고 가상 병원(`is_demo`) 행부터
- 바뀐 계약·코드: 없음

### 2026-11-17 (6) · backend-A-migration-0007 · Claude (Supabase 연결 해결)
- 한 일: 이 PC(스마트 앱 컨트롤 차단 모드)에서 **Supabase 연결 됨** — psycopg 바이너리(DLL)는 계속 막히지만, 설치된 **PostgreSQL 18 공식 `libpq.dll`**(서명됨)은 통과 → psycopg 순수 파이썬 구현으로 접속
  - 실행 전 (PowerShell, 그 창에서만): `$env:PATH = "C:\Program Files\PostgreSQL\18\bin;$env:PATH"; $env:PSYCOPG_IMPL = "python"`
  - 그다음 평소처럼 `uv run python -m alembic -c backend/alembic.ini upgrade head` / `uv run python -m uvicorn main:app --app-dir backend/src`
- 확인 (읽기 전용): `.env` = `AXA`(`afypgiqkrohgoybqhtsi`) · alembic `0006` · hospitals 4,242 · 등록 126 · public 테이블 11개
- 바뀐 계약·코드: 없음 (환경만)
- 다음 할 일: #29 머지 후 이 PC에서 0007 적용 가능 (`medi`·`AXA` 둘 다면 둘 다). B PC도 같은 방법 시도 가능 (PostgreSQL 설치 → bin을 PATH)

### 2026-11-17 (4) · backend-A-migration-0007 · Claude (리뷰 반영)
- 한 일: 점검([review-0007-2026-11-17.md](review-0007-2026-11-17.md)) 반영
  - `consents.booking_request_id` → `booking_requests.id` FK(SET NULL, 동의 증명은 남김)를 모델과 **0007**에 추가 (Supabase 미적용이라 0008 대신 0007에 포함. SQLite는 `batch_alter_table`)
  - 테스트 DB에서 **SQLite FK 검사 켬**(`conftest.py` `PRAGMA foreign_keys = ON`) → Postgres처럼 없는 id를 막음. 켜자 21개 실패: 없는 병원 9001로 병원 계정(B 테스트 20), 없는 요청서 id로 동의(A 1) → 새 `tests/db_rows.py`(`demo_hospital`·`demo_staff`, 가상 행)로 FK 대상 행을 먼저 만들게 고침
  - 사후관리 답장 테스트는 아무 uuid의 직원 토큰을 썼음 → `aftercare_messages.staff_id` FK 때문에 **Postgres였다면 500**. 실제 직원 행으로 토큰을 만들게 고침
  - 동의 테스트 2개 추가: 요청서 삭제 → 동의 남고 `booking_request_id`만 비움, 없는 요청서 id → 저장 실패
- 확인: 실제 데이터 로컬 SQLite 복사본에서 `upgrade head` → `downgrade 0006` → `upgrade head`, 병원 4,242 유지, `foreign_key_check` 0건. ⚠️ 예전 0007을 로컬에 올렸다면 `downgrade 0006` 후 다시 `upgrade head`
- 알게 된 것: 0001~0007 모든 CHECK 이름이 `ck_<표>_ck_<표>_<이름>`(이름 규칙이 두 번 붙음, Supabase에도 이 이름). 모델 이름(`ck_<표>_<이름>`)과 다름 → 이번엔 그대로 두고 정리 리비전은 따로
- 바뀐 계약: 없음 · 마이그레이션: `0007` 수정 (Supabase 미적용)
- 테스트: 백엔드+AI 368개 통과
- 다음 할 일: 요청서 제출 API, 직원 로그인
- B에게 요청:
  1. B 테스트 2개(`test_booking_tenant.py`·`test_aftercare_tenant.py`)의 `_tenant`에 `demo_hospital()` 한 줄, 사후관리 흐름 테스트에 `demo_staff()` — FK 때문에 필요, 리뷰에서 확인
  2. `seed_demo.py`가 `hospital_id=9001`(없는 병원)로 tenant를 만듦 → 로컬 SQLite는 FK 검사가 꺼져 있어 지금은 되지만 Supabase에서는 실패. 시드에 가상 병원 행(`is_demo=True`)을 먼저 넣거나 실제 `hospitals.id` 사용
  3. 직원 토큰의 `staff_id`가 `staff_users`에 없으면 답장·사후관리 저장이 500 → `current_staff()`에서 직원 행 확인(11/12 요청 ③)은 A가 직원 로그인 만들 때 같이

### 2026-11-17 (3) · backend-A-migration-0007 · Claude
- 한 일: **마이그레이션 `0007`** — B 모델(#28)의 `tenants`·`staff_users`·`booking_requests`·`booking_events`·`replies`·`aftercare_threads`·`aftercare_messages` + RLS. B 모델 주석대로 `tenants.hospital_id`·`booking_requests.hospital_id` → `hospitals.id` FK를 모델과 리비전에 추가 (병원 행은 지우지 않으므로 삭제 동작 없음)
- 새 테스트 `test_migrations.py`: 빈 SQLite에 `upgrade head` → 모델과 **테이블·칸·FK**가 같은지(`compare_metadata`), `downgrade 0006` → 다시 `upgrade`. FK 하나를 일부러 빼면 실패하는 것 확인. alembic.ini를 읽지 않게 해서 다른 테스트의 로그 캡처를 끄지 않음
- 확인: 실제 데이터가 든 로컬 SQLite(0006)에 `upgrade head` → `downgrade 0006` → `upgrade head` 정상, 병원 4,242곳 유지
- 바뀐 계약: 없음 · 마이그레이션: 있음 `0007` (**Supabase 미적용** → 다른 PC에서 `uv run python -m alembic -c backend/alembic.ini upgrade head`, 공용 DB가 `medi`·`AXA` 둘이면 둘 다)
- 테스트: 백엔드+AI 366개 통과
- 다음 할 일: 요청서 제출 API (`POST /hospitals/{id}/booking-requests`: `require_requestable` + 동의 4개 + 거주 재확인 → B `booking.service.create_request`)
- B에게 요청: 모델을 더 바꾸면 A에게 알려 주기(리비전 추가). #28 리뷰의 사후관리 비의료 제한·`health` 동의 확인

### 2026-11-17 (5) · backend-A-contract-registered → backend-A-registered-only · Claude
- 한 일: **병원 정보 공개도 등록 병원만** (결정 21, 결정 20 변경 — 복지부·진흥원 회신: 외국어 병원 정보 웹도 유치행위로 평가될 수 있음)
  - `hospital.service`: `PUBLIC_REGISTERED_ONLY = True` 한 곳에서 거름 → `GET /hospitals`(`ids`·`registered=false` 포함)는 등록 병원만, 미등록 상세는 없는 병원과 같은 404 `not_found`. 챗봇 찾기·상세도 이 서비스를 쓰므로 같이 적용(`registered_only=False`여도 미등록 X). `get_basic`·`require_requestable`(내부)은 그대로
  - **DB는 4,242곳 그대로** (등록 명단이 바뀌면 적재가 `is_registered_facility`만 갱신, FK 대상 유지)
  - 테스트: `files()`가 등록 명단을 안 받으면 모두 등록으로 적재(정렬·필터 테스트 유지), 새 규칙 테스트 — 목록 등록만·DB 전체 유지, 명단에서 빠지면 공개에서 빠지고 다시 등록되면 같은 id, 미등록 상세 404, 챗봇 `registered_only=False`·미등록 상세 카드 없음
- 확인 (실제 데이터 로컬 SQLite): 목록 126(미등록 0, 요청 가능 126) · 피부과 8 · 성형외과 11 · 내과 36 · 안과 8 · 미등록 상세 404 · DB 4,242
- 바뀐 계약: 있음 4절 + 결정 21 (`backend-A-contract-registered`, **B 확인 필요**)
- 테스트: 백엔드+AI 366개 통과
- 다음 할 일: 프론트 정적 `hospitals.json`도 등록 병원만 (프론트 브랜치), `compliance.md` 2-1·3절 5번 갱신(docs-compliance 쪽)
- B에게 요청: 결정 21·contracts 4절 확인. 대시보드는 `get_basic()`을 쓰므로 영향 없음
- AI 담당에게: `ai/agent/tools/chat_tools.py` `registered_only` 인자는 백엔드에선 효과 없음(항상 등록만) → 도구 설명·가상 병원 데이터도 맞출지 확인

### 2026-11-17 (8) · backend-A-contract-reject-reason → backend-A-reject-reason · Claude
- 한 일: **병원 직원 거절 사유 코드** (사용자 요청) — `fully_booked`·`not_offered`·`needs_consult`·`other`, 선택. `booking_events.reason`(20자, 이미 있음)에 저장 → 마이그레이션 없음. 거절이 아닌 행동에 사유·목록 밖 코드는 422
  - **B 모듈(booking) 변경**: `models.REJECT_REASONS`, `service.staff_act(reason=)`, `schemas.StaffAction.reason`, `router_tenant` 전달 — B 리뷰 필요
  - 같이: 대시보드 시안(`dashboard-dialogs` 브랜치, B의 `docs-dashboard-integration` 위)에 모든 버튼 확인 다이얼로그 + 요청 목록 DB 연결
- 확인: Supabase `AXA`(0007) + 가상 병원 9001로 대시보드에서 확정·시간 제안(직접 입력)·거절(사유 저장 `fully_booked` 확인)·방문 완료·사후관리 해결됨(태그)·답장 저장
- 바뀐 계약: 있음 2절 (거절 사유)
- 테스트: 백엔드+AI 367개 통과 (거절 사유 3개 추가)
- B에게 요청: ① 거절 사유 코드·계약 2절 확인 ② 대시보드 다이얼로그 PR 리뷰 ③ 환자 화면에 거절 사유를 언어별 문장으로 보일지 결정

### 2026-11-18 (2) · backend-A-manual-hours · Claude
- 한 일: 직접 채운 진료시간에 `override=Y` 지원 — 카카오맵 영업정보로 전체 검증해 보니 심평원 API 값이 실제와 다른 곳(9곳)이 있어서, 그 행은 API 값이 있는 요일도 바꿈. `휴진`으로 바뀌면 시간 칸 비움
- 데이터 쪽 결과: [진료시간-채움-등록기관-2026-11-18.md](진료시간-채움-등록기관-2026-11-18.md) 0-2 (카카오 138곳: 일치 46 · 변경 48 · 채움 24 · 확인 불가 20), 로더용 파일은 research-data 브랜치
- 바뀐 계약: 없음 · 마이그레이션: 없음
- 테스트: 169개 통과 (새 1개: override=Y면 API 값 대체, 빈 요일은 API 유지). 실제 데이터 + `daegu_hours_manual.csv` 101행 메모리 SQLite 적재 → `manual_hours: 101`, 등록 126곳 중 평일 5일 확인 121곳
- 다음 할 일: 공용 DB 정한 뒤 Supabase 재적재 · 네이버/홈페이지 교차확인은 데이터 담당
- B에게 요청: 없음

### 2026-11-18 · backend-A-manual-hours · Claude
- 한 일: 병원 적재가 **직접 채운 진료시간**도 읽게 함 (결정 21로 공개 = 등록 유치기관만 → 그 기관 진료시간 빈칸을 직접 채우기로, [진료시간-채움-등록기관-2026-11-18.md](진료시간-채움-등록기관-2026-11-18.md))
  - 그전에는 `loader.py`가 심평원 API CSV만 읽어서 10/28에 직접 채운 값도 DB·화면에 안 나갔음
  - `load_hospitals(manual_hours_csv=…)`, 스크립트 기본 경로 `data/processed/daegu_hours_manual.csv` (없으면 건너뜀). 칸: `ykiho`, `mon`~`sun`(`HH:MM-HH:MM` / `휴진` / 빈칸), `lunch_week`·`lunch_sat`, `source_url`, `checked_at` — 작업표 `registered_hours_fill.csv` 형식 그대로 읽힘
  - 규칙: **API 값이 없는(state=unknown) 요일만** 채움 · `휴진` → closed · 빈칸·형식 틀림·시작≥끝 → unknown 유지 · 출처(`source_url`)·확인일 없는 행은 적재 X · `hospital_hours.source`·`checked_at`은 요일마다 실제 출처 · 적재 결과에 `manual_hours` 건수
  - 상세 API `hours[]`에 `source`·`checked_at` 추가 (요일마다 출처가 다를 수 있어서, 칸 추가만)
- 바뀐 계약: 없음 (상세 응답 `hours[]`에 칸 2개 추가 — 프론트에 알림) · 마이그레이션: 없음 (기존 칸 사용)
- 테스트: 168개 통과 (새 4개: API 우선·빈 요일만 채움·휴진/빈칸, API 행 없는 병원, 형식 틀림 무시, 출처 없는 행 적재 X). 실제 데이터 4,242곳 + 작업표(1행 시험 값)로 메모리 SQLite 적재 확인 → `manual_hours: 1`, 그 병원 월=open·토=closed·출처 URL
- 다음 할 일: 데이터 담당이 채운 뒤 `data/processed/daegu_hours_manual.csv`로 → Supabase 재적재 (공용 DB 정한 뒤) · 프론트 `build-hospitals.mjs`도 같은 파일 읽게
- B에게 요청: 없음
- 막힌 것·질문: 없음

### 2026-11-18 (3) · backend-A-booking-request · Claude
- 한 일: **환자 예약 요청 · 내 예약 API** (`modules/booking/router_patient.py`, `schemas_patient.py`) — 흐름이 "요청서 제출"에서 "예약 요청 → 병원 확정"으로 바뀐 것에 맞춤
  - `POST /hospitals/{hospital_id}/booking-requests` → 201 `PatientBookingOut`: `require_requestable`(미등록·영업 중 아님 403) → 입점(tenant·requests_enabled) 확인(없으면 403 `hospital.not_requestable` `reason=not_joined`) → 동의 확인 → `booking.service.create_request`(B) → 동의를 요청서에 묶어 기록(`consents.booking_request_id`)
  - 동의 규칙: `privacy` 항상 · `health_info` 있으면 `health` · `message`/`health_info` 있으면 번역(해외 LLM)용 `overseas_transfer` → 없으면 422 `consent.required`(`detail.missing`)
  - `residency`는 `short_term`만 (국내 거주 외국인 유치 X, 의료법 제27조 제3항 제2호) · 희망 일시 1~3개, 시간대 포함, 미래만
  - `GET /me/booking-requests`·`/{id}` (내 것만, 남의 것 404, 답장은 `sent_at` 있는 것만) · `POST …/accept`(proposed→confirmed) · `POST …/cancel {reason?}`(pending·proposed만)
- 공통 파일 변경 (B 승인 필요): `main.py` 라우터 1줄
- 바뀐 계약: 있음 — 4절 `not_joined` 사유, 6절 `residency` 필수·동의 규칙 → contracts PR 따로 (`backend-A-contract-booking-request`)
- 마이그레이션: 없음 (테이블은 0007, PR #29)
- 테스트: 180개 통과 (새 `test_booking_patient.py` 16개: 생성·동의 묶기, 401·직원 403, 미등록·폐업·미입점 403, 없는 병원 404, 동의 3종, 국내 거주 422, 희망 시간 개수·과거, 중복 409, 내 것만·남의 것 404, 병원 확정 → 내 예약 confirmed, 제안 수락·확정 뒤 취소 409, 취소 사유)
- 다음 할 일: 프론트 상담·내 예약 화면을 이 API로 (지금은 브라우저 저장) · 직원 로그인 · 알림 · 요청 횟수 제한
- B에게 요청: `main.py` 1줄·`schemas_patient.py`(booking 폴더 안 A 파일) 확인
- 막힌 것·질문: 시연하려면 공용 DB에 0007 적용 + 등록 병원 1곳에 tenant 행(입점) 필요

### 2026-11-18 (4) · backend-A-staff-auth · Claude
- 한 일: **가입할 때 환자/병원 관계자 나눔** — 병원 쪽 가입·로그인 (`modules/auth/staff.py`)
  - `POST /auth/staff/signup` {email, password, hospital_id, registration_no, consents} → 201 직원 토큰: 등록 유치기관·영업 중만(`require_requestable`, 403/404) → 병원 1곳 = 계정 1개(이미 입점 409 `auth.hospital_taken`) → `tenants`(requests_enabled=True, 등록번호) + `staff_users`(owner) 생성
  - `POST /auth/staff/login` → 직원 토큰(`tenant_id`). 실패 응답 하나로, 시도 제한(환자와 기록 분리), 비활성 직원 401
  - 프로토타입: 등록번호는 형식(`M-YYYY-MM-DD-NNNN`)만 확인 → 실서비스는 운영자 확인 후 활성화 (팀 확인)
- 바뀐 계약: 있음 — 4절 `auth.hospital_taken`, 직원 가입·로그인 경로 → contracts PR 따로 (`backend-A-contract-staff-auth`)
- 마이그레이션: 없음 (tenants·staff_users는 0007, PR #29)
- 테스트: 175개 통과 (새 `test_auth_staff.py` 11개)
- 다음 할 일: 직원 추가 초대(owner가 staff 추가) · `current_staff()`가 직원 행·비활성 확인 (지금은 토큰만 → 비활성돼도 만료 전까지 사용 가능, core 변경이라 B 승인 필요)
- B에게 요청: `tenants`·`staff_users`에 A가 행을 만드는 것 확인

### 2026-11-17 (2) · backend-A-hospital · Claude (로컬 확인)
- 한 일: 프론트(5173)·백엔드(8000) 로컬 실행 확인. 백엔드를 **로컬 SQLite**(0001~0006 + 실제 데이터)로 켜면 `/hospitals`·상세·정렬 422·프론트에서 호출(CORS) 모두 정상. **Supabase 설정으로 켜면 서버는 뜨지만 DB를 쓰는 요청은 500**(`ImportError`, psycopg)
- 원인: 이 PC의 윈도우 **스마트 앱 컨트롤이 차단 모드**(`VerifiedAndReputablePolicyState = 1`), CodeIntegrity 로그에 psycopg DLL 차단(11/17 14:59·15:34). 11/4~5에는 이 PC에서 Supabase 연결이 됐음(아래 기록) → 그 뒤 차단 모드로 바뀐 것으로 보임. B PC도 11/12 같은 증상
- 정한 것(사용자): **Supabase 연결 확인은 다른 PC에서**. 이 PC는 SQLite로만 확인. (대안: PostgreSQL 공식 libpq 설치 후 PATH — 서명된 DLL이라 통과 가능성, 미확인)
- 확인: 두 Supabase 프로젝트 모두 회원·동의·세션·챗봇 대화 0건 (예전 테스트 계정은 11/5 초기화로 삭제)
- 바뀐 계약: 없음 · 테스트: 342개 통과 (변경 없음)

### 2026-11-17 · backend-A-hospital · Claude (Supabase 적용)
- 한 일: **Supabase 공용 DB에 `0005`·`0006` 적용 + 병원 4,242곳 적재** ([supabase-병원-0006-적용.md](supabase-병원-0006-적용.md) 절차 그대로, macOS에서 실행). DB가 `0004`에 있어서(0005 챗봇 대화 테이블도 미적용이었음, 같은 선형 체인이라 분기 없음) `upgrade head`로 둘 다 적용. 세션 풀러(5432)로 실행 (`.env`는 6543 그대로, 실행 시만 환경변수로 바꿈)
- **같은 날 두 번째 프로젝트에도 적용**: 이 PC `.env`가 `afypgiqkrohgoybqhtsi`(`aws-1`, 세션 풀러 5432 — 아래 교차 확인의 `AXA` 프로젝트로 보임)로 바뀌어 빈 DB에 `0001→0006` 전체 적용 + 병원 재적재. 아래 확인값 동일. ⚠️ 지금은 **`medi`·`AXA` 두 프로젝트 모두 같은 스키마·데이터** → 팀이 공용 DB를 하나로 정하고 각자 `.env`·Vercel 환경변수를 맞출 것
- 확인 (SQL): hospitals 4,242 · 등록+정상 126 · 비정상 31 · 진료과 dermatology 80 / internal 1,301 / ophthalmology 300 / plastic 70 · hospital_hours 29,694 · RLS 6개 테이블(hospitals 4개 + chat 2개) 모두 켜짐 · alembic_version `0006`
- 바뀐 계약: 없음
- 테스트: 없음 (DB 적용만)
- 다음 할 일: PR 리뷰에서 0006 구조가 바뀌면 `downgrade 0005` 후 다시 적용. backend → main 머지·배포 후 `/api/v1/hospitals` 확인
- B에게 요청: Supabase에 `chat_sessions`·`chat_messages`(0005)도 이제 있음 — 로컬 `alembic current`가 `0006`인지 확인
- 막힌 것·질문: 없음
- 교차 확인 (백엔드 A PC, 대시보드 SQL Editor 읽기 전용, 15:2x): org `medi`의 **두 프로젝트 모두** 0006·위 숫자와 같음 + "0000~0000"을 진료로 넣은 줄 0 + public 테이블 RLS 꺼진 것 0 — `medi`(`wlzaddcemtpihtpbwkgn`) 먼저, **`AXA`(`afypgiqkrohgoybqhtsi`)는 15:22에 적재**(처음 확인 땐 비어 있었음). ⚠️ 공용 DB가 둘 → 팀이 하나로 정하고 각자 `.env`·Vercel `DATABASE_URL`을 맞출 것 (백엔드 A PC `.env` = `AXA`)

### 2026-11-17 · backend-A-hospital · Claude
- 한 일: ① `backend-A-contract-hospital`을 합치고 `hospital.service.require_requestable()` (미등록 → 403 `hospital.not_requestable` `reason=unregistered`, 폐업·미확인 → `not_operating`, 없으면 404) — 요청서 API가 생기면 이것만 부름 ② `GET /hospitals?open_on=mon..sun` (그 요일 진료가 확인된 병원만, 시간 정보 없음은 제외) ③ **챗봇 병원 찾기·상세를 실제 병원 DB로**: `modules/chatbot/hospitals.py` `HospitalGateway` → `ChatService(hospitals=…)` → `ToolContext.hospitals`. 게이트웨이가 없으면(ai 테스트·eval) 가상 병원 그대로 ④ 적재: 원본 "0000~0000"은 진료로 보지 않음(`unknown`, 일요일 23곳)
- 정한 것(사용자, 2026-11-17): 찾기·상세만 실제 DB, **조건 맞춤 제안·예약은 아직 가상 병원**. 실제 병원은 응대 언어 정보가 없어 언어로 거르지 않고 "병원에 확인" 안내(`staff_languages = []`). 상세 카드의 진료시간은 확인된 요일만(시간 정보 없는 요일은 휴진(None)으로 보이지 않게 뺌)
- **피부과·성형외과 = 전문 병원만 (사용자 결정 2026-11-17)**: `has_dermatology = Y` + 이름에 "피부과" → 818곳 → **80곳(모두 의원), 등록 8곳**. 대학병원·한방병원·정형외과는 빠짐. 프론트 `hospitals.json`(build-hospitals.mjs)은 아직 진료과목 코드 기준(814곳) → 프론트에 알릴 것. **성형외과도 같은 기준** (256곳 → 70곳, 등록 11곳). 실제 병원 id로 예약 초안을 만들면 아직 "병원 없음" (예약은 가상 병원 9001~)
- 바뀐 계약: 없음 (계약 브랜치 내용을 합침. PR 순서 = `backend-A-contract-hospital` → `backend-A-hospital`)
- 테스트: 백엔드+AI 339개 통과 (병원 +2, 챗봇 병원 3개 새로, 기존 챗봇 테스트 1개는 DB에 병원을 넣도록 고침). 실제 데이터(로컬 SQLite)로 수성구 토요일 등록 피부과 검색·상세 확인
- 다음 할 일: 조건 맞춤 제안을 실제 DB로 (언어는 "모름", 아는 것만 이유로), 가상 병원을 DB에 `is_demo`로 넣고 예약을 거기로
- B에게 요청: 계약 4·5절 확인 (`backend-A-contract-hospital`)
- Supabase 적용: 이 PC는 psycopg DLL이 정책에 막혀 실행 못 함 → **다른 팀원 PC에서 실행**하기로 함. 안내 `docs/supabase-병원-0006-적용.md` (기대값을 로컬 SQLite로 미리 확인: 4,242 · 요청 가능 126 · 피부과 80 · 성형외과 70 · 진료시간 29,694). PowerShell `git show > 파일`은 UTF-16으로 저장돼 등록 병원 0곳이 됨 → 안내는 `git restore --source`, 적재는 JSON BOM도 읽게 고침

### 2026-11-16 · backend-A-hospital · Claude
- 한 일: **병원 데이터 API** — 테이블 `hospitals`·`departments`·`hospital_departments`·`hospital_hours`(마이그레이션 `0006`), 적재 `modules/hospital/loader.py` + `backend/scripts/load_hospitals.py`(ykiho로 upsert, 행 삭제 X, 새 파일에 없는 병원은 `closed`), `GET /hospitals`(필터 `sggu`·`dept`·`registered`·`ids`, 정렬 `name`·`distance`만, 그 밖 422, 폐업 제외), `GET /hospitals/{id}`(진료시간·출처·수집일, 없으면 404 `not_found`), `hospital.service.get_basic()`
- 팀 결정(2026-11-16): **병원 정보는 전체, 상담·예약은 등록 병원만** → 응답에 `is_registered_facility`·`can_request`(= 등록 유치의료기관 + 영업 중). 정렬에는 반영 X (해외진출법 제24조①3, compliance 2-1)
- 스키마 2절과 다른 점: `type_name_ko`(종별 이름)·`hospital_hours.day_order`(요일 정렬) 추가. 진료시간 값이 없으면 휴진으로 단정하지 않고 `unknown`
- 실제 데이터 확인(로컬 SQLite): 4,242곳 적재, 목록 4,233곳(폐업 9 제외), 등록 126곳 = 요청 가능 126곳. 진료과: 내과 1,301·피부과 818·안과 300·성형외과 256 (내과·안과는 심평원 진료과목 코드 기준이라 프론트 `hospitals.json` 1,267곳과 기준이 다름 → 프론트와 맞출 것)
- 바뀐 계약: 없음 (5절 `HospitalBasic` 칸을 처음 정함: id·ykiho·name_ko/en·type_code·sggu·addr_ko·tel·is_registered_facility·is_demo·can_request) → B 확인
- 마이그레이션: 있음 `0006` (SQLite에서 upgrade·downgrade·upgrade 확인, Supabase는 아직)
- 테스트: 백엔드 134개 통과 (병원 9개 추가)
- 다음 할 일: 등록 파일(`daegu_registered_institutions.csv`)·내과/안과 파일이 `research-data`에만 있음 → 적재 때 `--registered-csv`·`--dgsbjt-json`으로 경로를 주거나 main에 합친 뒤 실행. 시연용 가상 병원(`is_demo`) 시드 만들 때 `can_request`에 포함. 요청서 API에서 `get_basic().can_request`가 false면 막기(에러 코드는 contracts 4절에 새로 추가 필요)
- B에게 요청: `HospitalBasic` 칸 확인
- 막힌 것·질문: 이 PC에서 `alembic` 실행 파일이 정책에 막힘 → `uv run python -m alembic -c backend/alembic.ini …`로 실행

### 2026-11-12 · backend-review-fix · Claude
- 한 일: 코드 리뷰(`docs/review-branches-2026-11-12.md`, ai 브랜치) 반영. 공통 500 `internal`(ASGI 미들웨어) · 동시 가입 409 · 정리 API `/internal/purge`(`CRON_SECRET`) · 환율 ECOS 실패 뒤 10분 저장값·첫 요청 경쟁 · 로그인 시도 제한 `auth.too_many_attempts` · 챗봇 새 대화를 한 트랜잭션으로 · auth 세션 함수 commit 규칙 통일 · PATCH display_name 공백 · JWT HS256 고정 · 가입 동의 현재 버전 검사 · `patient_uuid`를 core/security로 · `.env.example`(`CRON_SECRET` 추가, `JWT_ALGORITHM` 삭제)
- 바뀐 계약: **있음** 1·4·7-1절 (변경 이력에 기록) → **B 승인 필요**
- 마이그레이션: 없음
- 테스트: 315개 통과 = 백엔드 125 + AI 190 (`uv run --no-sync python -m pytest backend/tests ai/tests`). 이 PC는 SQLAlchemy C 확장 DLL이 정책에 막혀 worktree venv에서만 순수 Python으로 재설치함
- 다음 할 일: Vercel Cron 설정(`vercel.json`) · 챗봇 `state` 동시 저장 충돌 처리 방식 결정
- B에게 요청: ① contracts 1·4·7-1절 확인 ② PK 이름(`<table>_pkey` vs 모델 `pk_<table>`)·server_default 차이 정리 마이그레이션 (B가 마이그레이션 담당) ③ `current_staff()` 직원 토큰 DB 확인 ④ `modules/agent/` 빈 폴더 유지 여부
- 막힌 것·질문: Vercel에서 `request.client.host`가 실제 사용자 IP인지 (프록시 IP면 IP 제한이 모두를 같이 막음)

### 2026-11-11 (2) · backend-A-chatbot · Claude
- 한 일: **7e 지난 대화** — `GET /chatbot/sessions`(내 대화 목록, 최근 순, 최대 50), `GET /chatbot/sessions/{id}`(가린 글만, 카드·상태 X). **7c 계약·문서** — contracts 7절 챗봇 API 신설, 4절 `chatbot.unavailable`·`rate_limited` 챗봇 추가, 5절 챗봇의 `booking.service` 호출, 6절 `lang` 5개·`department_code` 값·`residency` 제안. `backend-plan.md` API 표, `compliance.md`(추천 허용 범위·대화 저장·AI 표시) 갱신. 수동 검증 안내 `docs/7b-수동검증.md`(Swagger·curl)
- 바뀐 계약: **있음** 4·5·6·7절 (변경 이력에 한 줄) → **B 승인 필요**
- 마이그레이션: 없음
- 테스트: 290개 통과 = 백엔드 100(챗봇 API 12) + AI 190. 실제 서버 + 프론트(`frontend-chatbot-api`)로 확인: 새로고침 뒤 지난 대화 목록·내용이 서버에서 다시 보이고, 이어서 질문하면 같은 대화에 저장됨(로컬 SQLite)
- 다음 할 일: 이 브랜치 → `backend` PR, 머지 뒤 공용 DB에 `0005`, 프론트 PR, 병원 데이터(`hospital` 모듈)
- B에게 요청: ① contracts 4~7절 변경 확인 ② `BookingCreate`에 `residency`(체류 형태) 칸 또는 계정 속성 의견 ③ `booking.service.list_for_patient`·`get_for_patient`가 오면 챗봇 연결
- 막힌 것·질문: 없음

### 2026-11-11 · backend-A-chatbot · Claude
- 한 일: **7b 챗봇 API** — `origin/ai`를 이 브랜치에 merge(백엔드가 `ai.agent` 서비스 층을 import). `modules/chatbot/`에 `store.py`(`SessionStore`의 DB 구현, 환자 id로 범위 제한, 잘못된 id는 "없음"), `bookings.py`(예약 조회 게이트웨이 — `booking` 모듈이 없어 지금은 "내 요청 없음", 가짜 예약 데이터는 실제 환자에게 안 보임), `schemas.py`(`AskRequest`), `service.py`(계정의 시간대·선호 언어 채우기, `ChatServiceError` → `AppError`), `router.py`(`POST /chatbot/ask`, `DELETE /chatbot/sessions/{id}`, 모두 환자 로그인 필요). `main.py`에 라우터 등록. 응답은 `ai.agent.schemas.ChatResponse` 그대로(카드 9종이 OpenAPI에 나옴)
- 바뀐 계약: 없음. 단 **`chatbot.unavailable`(503)은 계약 4절에 아직 없음** → 7c 계약 PR에서 추가 (`/chatbot/*` 경로·카드 형식도 같이)
- 마이그레이션: 없음 (`0005` 그대로, 공용 Supabase 미적용)
- 테스트: 288개 통과 = 백엔드 98(기존 88 + 챗봇 API 10) + AI 190. 챗봇 API: 로그인 필요, 입력 검사, DB에 가린 텍스트만 저장, 다음 턴이 DB 기록·상태로 이어짐("보여 준 병원" 복원), 초안에 `health_info`·문의 내용 저장 X, **다른 환자의 대화 이어 쓰기·삭제 404**, 내 대화 삭제, 탈퇴 시 대화 삭제, 429, LLM 전부 실패 시 503·저장 안 함. 이 PC에서 `uv sync` 후 정상 실행됨(11/10의 sqlalchemy 확장 차단은 이번엔 없었음)
- 다음 할 일: 이 브랜치 → `backend` PR, 공용 DB에 `0005` 적용, 7c 계약 PR, 7d 프론트 연결
- B에게 요청: ① `booking.service.list_for_patient(db, patient_id, status)`·`get_for_patient`가 생기면 `modules/chatbot/bookings.py`만 바꾸면 챗봇의 "내 요청 상태"·제출 확인이 동작함 ② 7c 계약 PR 리뷰
- 막힌 것·질문: ① 호출 제한이 프로세스 메모리라 Vercel 여러 인스턴스에서는 따로 셈 → 운영 전 DB·캐시로 ② 이 PR에는 `ai` 브랜치 변경이 함께 들어감(`ai` → `main` PR이 먼저 머지되면 겹치는 부분은 사라짐). 병원 검색 도구는 아직 `ai`의 가상 병원 데이터를 씀 (`hospital` 모듈 생기면 교체)

### 2026-11-10 · backend-A-chatbot · Claude
- 한 일: **챗봇 대화 테이블** — `modules/chatbot/models.py`(`ChatSession`·`ChatMessage`), 마이그레이션 `0005`(`chat_sessions`·`chat_messages`, RLS 켬), `sessions.py`(`delete_all`·`purge_older_than`), `auth.service.withdraw`가 챗봇 대화도 즉시 삭제, `core/db_models.py` 등록. 결정 16 기록, db-schema 5절·backend-plan 로그인 표 갱신
- 바뀐 계약: 없음 (`/chatbot/*` 계약은 7c에서 별도 PR). 단 **이전 결정 3 일부 변경(챗봇 로그인 필요)** — 결정 16
- 마이그레이션: 있음 `0005`. **공용 Supabase에는 아직 적용하지 않음**(PR 머지 뒤 `alembic upgrade head`)
- 테스트: 88개 통과 (기존 78 + 챗봇 테이블 10). `alembic upgrade head`(0001~0005, 임시 SQLite)·`alembic check`(모델과 일치)·`downgrade 0004`→`upgrade head`·PostgreSQL SQL 출력(JSONB, identity, ON DELETE CASCADE, RLS) 확인. 탈퇴 삭제 연결을 빼면 테스트가 실패하는 것도 확인
- 다음 할 일: `SessionStore` 인터페이스(`ai/agent/session_store.py`)의 DB 구현 + `POST /chatbot/ask` 라우터(`ai` 브랜치가 `main`에 들어온 뒤 — 지금 `backend`에는 `ai/` 패키지가 없음), 계약 PR
- B에게 요청: 결정 16(챗봇 로그인 필요, 요청서는 같은 API로 제출) 확인. 병원 쪽 `booking.service.create_request`·`list_for_patient`가 오면 챗봇이 제출 확인에 씀
- 막힌 것·질문: ① 증상을 쓰면 건강정보가 계정에 저장되어 AGENTS.md 6절과 충돌(스키마 5절 ⚠️) — 고지·마스킹·30일·삭제 버튼으로 진행하되 **팀 확인 필요**, 개인정보보호위원회 질의 8번 회신 전. 요청서 초안의 `health_info`는 저장 상태에서 빼는 것이 안전(7a 서비스 층에 반영 예정) ② 이 PC는 보안 정책이 `sqlalchemy`의 컴파일된 확장 파일을 막아, 일회용 가상환경에서 그 파일만 지우고 순수 파이썬으로 테스트함(팀 환경·`uv.lock` 무관, 속도만 느림)

### 2026-11-05 (3) · backend-A-account · Claude
- 한 일: **Supabase DB 초기화** — `alembic downgrade base` → `upgrade head`로 `0001`~`0004` 다시 적용 (현재 `0004`, 모든 테이블 비어 있음, RLS 켜짐). 기존 테스트 계정 3개·세션·동의 삭제. 아래 항목의 "Supabase 미적용"은 이걸로 처리
- 바뀐 계약: 없음
- 테스트: 78개 통과 (변경 없음). 테이블 목록·행 수·RLS 확인
- 다음 할 일: 찜·방문 기록 API
- B에게 요청: 공용 Supabase에는 `@example.com` 가짜 계정만 (실제 메일 X). DB가 비었으니 테스트 계정은 새로 가입
- 막힌 것·질문: 없음

### 2026-11-05 (2) · backend-A-account · Claude
- 한 일: **탈퇴 = 즉시 삭제** (결정 15). `DELETE /me` → 비밀번호 확인 → 세션 전부·`patients` 행 삭제, 동의 기록은 남기고 `patient_id`만 비움(`consent.detach_patient`). `deleted_at` 칸·부분 UNIQUE 제거 → 이메일 일반 UNIQUE, `patient.get_live*` → `get`·`get_by_email`. 마이그레이션 `0004`(예전 탈퇴 표시 행 정리 후 칸 삭제) — **Supabase 미적용** (`0003`과 같이)
- 바뀐 계약: 없음 (응답 그대로, 변경 이력에 한 줄)
- 테스트: 78개 통과 (탈퇴: 내 행·세션 삭제, 다른 환자 그대로, 동의 4개 중 내 것 2개 `patient_id` 비움, 바로 재가입). SQLite로 `0004` 올리기·내리기·다시 올리기 확인
- 다음 할 일: Supabase에 `0003`·`0004` 적용, 찜·방문 기록 API
- B에게 요청: 11/4 요청 중 "정기 삭제에 탈퇴 계정 파기"는 **취소** (탈퇴 즉시 삭제). 정기 삭제는 만료 세션(`sessions.purge_dead(db)`)·알림 90일 등만
- 막힌 것·질문: 없음

### 2026-11-05 · backend-A-account · Claude
- 한 일: `auth_sessions`가 계속 쌓이지 않게 `sessions.purge_dead()` 추가 — 만료됐거나 로그아웃한 세션 행 삭제. 로그인·가입할 때 그 환자 것만 정리, `patient_id` 없이 부르면 전체 (배포 후 cron용)
- 바뀐 계약: 없음
- 테스트: 79개 통과 (정리 2개 추가: 내 것만 지움·다른 환자 그대로·살아 있는 세션 유지)
- 다음 할 일: Supabase에 `0003` 적용, 찜·방문 기록 API
- B에게 요청: 배포 때 Vercel cron은 **하나로** (무료 플랜 하루 1번) — 그 안에서 환율 미리 받기 + `sessions.purge_dead(db)` 전체 정리를 같이
- 막힌 것·질문: 탈퇴 계정 행을 실제로 지우는 시점(보관 기간) 미정

### 2026-11-04 (2) · backend-A-account · Claude
- 한 일:
  - `DELETE /me` 탈퇴: 비밀번호 확인 → `deleted_at` + 모든 기기 로그아웃(`revoke_all`). 동의 기록은 남김, 같은 메일 재가입 가능. 실제 삭제(파기)는 정기 삭제 스크립트(B)
  - `modules/fx`: 환율 `GET /exchange-rates` — **한국은행 ECOS 731Y001**(주요국통화의 대원화환율, 일별)에서 USD·CNY·TWD·VND(100동당) → 1원당 외화로 저장. **매일 오전 10시(KST) 기준 "적용일"**(10시 전이면 어제)로 하루 1번만 받고, 다음 날 10시 전까지 같은 값으로 안내. 주말·공휴일은 직전 영업일 값. 실패하면 저장값(`stale`), 없으면 503 `fx.unavailable`. 키는 `.env` `ECOS_API_KEY`, 시각은 `FX_SWITCH_HOUR_KST`(기본 10)
  - 마이그레이션 `0003` `exchange_rates`(currency·rate·base_date·applied_on·fetched_at, +RLS) — **Supabase 미적용**
  - 프론트(`frontend-mypage-currency`): 마이페이지 "내 계정"을 탈퇴하기로(프로필·언어 설정 문구 제거, 비밀번호 확인 창), 가격 가이드 통화별 참고 환산(원화 같이 표시, 출처·기준 시각)
- 바뀐 계약: contracts 1절(`fx/` 주인 A)·4절(`fx.unavailable`)
- 테스트: 77개 통과 (탈퇴 3, 환율 16: 10시 전후·적용일 하루 1번·주말·VND 100동·실패). 임시 SQLite로 화면 확인 (탈퇴·틀린 비밀번호·데모 비활성, USD·VND·TWD·CNY × 언어)
- 다음 할 일: Supabase에 `0003` 적용, 찜·방문 기록 API
- B에게 요청: 정기 삭제 스크립트에 "탈퇴 계정 파기" 포함 / 배포 시 Vercel cron `0 1 * * *`(UTC 01:00 = KST 10:00)으로 `GET /api/v1/exchange-rates` 미리 호출(선택, 무료 플랜 ±59분), Vercel 환경변수에 `ECOS_API_KEY`
- 막힌 것·질문: ECOS에 당일 값이 몇 시에 들어오는지 미확인 (11/4 값은 오후 조회 시 있음) → 10시에 당일 값이 없으면 전 영업일 값, 화면에 기준일 표시

### 2026-11-04 · backend-A-auth · Claude
- 한 일:
  - DB: Docker 대신 Supabase + Vercel (결정 12). `core/db.py`(SQLAlchemy 2 동기 + psycopg 3, NullPool, prepared statement 끔, UTC 강제 `UTCDateTime`), `core/db_models.py`(모델 등록), `.env.example`에 `DATABASE_URL`
  - 마이그레이션은 A가 (결정 13). `backend/alembic.ini`(Windows cp949 때문에 ASCII만), `env.py`, 리비전 `0001` = `patients`·`auth_sessions`·`consents` + RLS(Supabase 공개 API 차단)
  - 로그인 방식: 이메일 인증코드 → **이메일 + 비밀번호 회원가입** (결정 11). `POST /auth/patient/signup`(201, 14세 확인 + `terms`·`privacy` 필수, 바로 토큰), `POST /auth/patient/login`(실패는 `auth.invalid_credentials` 하나, 없는 이메일도 해시 검증 시간 똑같이)
  - 로그아웃 즉시 무효 (결정 14): `auth_sessions` 테이블, 토큰에 `sid`, `current_patient()`가 요청마다 세션 확인, `POST /auth/patient/logout`(204, 이 기기만), `sessions.revoke_all()`(탈퇴·비밀번호 변경용)
  - `modules/patient`: `GET /me`, `PATCH /me`(언어·시간대·표시 이름만. 이메일·비밀번호는 못 바꿈). `modules/consent`: `record()`·`require()`
  - 프론트 연결: CORS(`CORS_ORIGINS`, 기본 localhost 5403·5173, 쿠키 X), 가입 시 `display_name`(선택) 받음, `/` → `/docs`. 프론트 회원가입·로그인 폼은 `frontend-auth` 브랜치 (프론트 담당 리뷰 필요)
  - `core/errors.py`: FastAPI 입력 오류도 `{code: "validation"}` 형식, `core/config.py`: `.env`를 파일 위치 기준으로 (PR #3 리뷰 의견)
- 바뀐 계약: contracts 1절(alembic 주인 A), 3절(환자 토큰 `sid`, 세션 확인), 4절(`validation` 형식, `auth.code_invalid` 삭제, `auth.invalid_credentials`·`auth.email_taken` 추가) — **B 확인 필요**
- 테스트: 58개 통과 (CORS·표시 이름·DB 주소 정규화 포함. 로그아웃 즉시 401·다른 기기 유지·전체 로그아웃·남의 세션 X 포함. 새 36개: 가입·해시 저장·이메일 정규화·중복·14세·필수 동의·입력 오류·로그인 실패 같은 응답·탈퇴 후 로그인 X·재가입·/me 권한·동의 require). 마이그레이션 = 모델 비교 차이 0, upgrade/downgrade 확인 (SQLite)
- Supabase: 연결 확인(PostgreSQL 17, 싱가포르 `ap-southeast-1`, 트랜잭션 풀러) → `0001`·`0002`(alembic_version RLS) 적용, 테이블 4개 RLS 켜짐·정책 0. 실제 DB로 가입·중복·로그아웃 즉시 401·재로그인 확인 후 테스트 계정 삭제. 한국 PC→싱가포르라 `/me` 약 0.7초 → Vercel은 `sin1`에 배포할 것
- 다음 할 일: Vercel 진입점(`sin1`). pgvector는 챗봇 때 마이그레이션으로 켜기. 요청서 환자 router(B `booking.service` 필요)
- B에게 요청:
  1. 결정 11~14, contracts 1·3·4절 변경 확인 (Docker 안 씀, 마이그레이션 A, 비밀번호 로그인)
  2. `staff_users`·`booking_requests` 모델 만들면 알려주기 → A가 마이그레이션 + `consents.booking_request_id` FK 추가
- 막힌 것·질문: 로그인 시도 제한·비밀번호 재설정(메일 필요)은 아직 없음. 비밀번호 규칙(8~128자)은 팀 확인

### 2026-11-03 · backend-A-auth · Claude
- 한 일: 전체 DB 스키마 초안 v3 [backend-db-schema.md](backend-db-schema.md) — 마이페이지(찜·방문 기록(리뷰 X)·여행 여러 개·일정 항목·알림함, 조회 기록·체크리스트 체크 상태는 브라우저 localStorage만), 챗봇 대화(로그인 시만), `patients.display_name`, `price_stats.scope` 추가. 프론트 마이페이지 코드(`origin/frontend` f8da9c6)에 맞춤
- 바뀐 계약: 없음 (제안 단계. 확정되면 contracts 1절 주인에 새 모듈 `favorite/trip/chatbot` 추가 PR)
- 테스트: 없음 (문서만)
- 다음 할 일: B 검토 후 `models.py` 작성, 마이페이지 API
- B에게 요청:
  1. 스키마 6절 `booking_requests.id`를 uuid로 (알림 FK)
  2. 확정되면 마이그레이션 생성
- 막힌 것·질문: 챗봇 대화 저장이 "환자 계정에 건강정보 저장 X"와 부딪힐 수 있음 → 팀 확인 (스키마 5절)

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
