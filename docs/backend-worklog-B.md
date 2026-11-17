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

### 2026-11-17 · backend-B-dashboard · Claude
- 한 일: 병원 대시보드 1단계(예약 지표) — `tenant`(`tenants`·`staff_users`), `booking`(`booking_requests`·`booking_events`·`replies`) 모델, 상태 흐름 `booking/service.py`(전이 규칙 한 곳, 변경마다 이벤트 1건, `visited`·`no_show` 추가), 병원용 API `router_tenant.py`(`GET /tenant/booking-requests`·상세, `POST …/confirm·reject·propose·visited·no-show`, `GET /tenant/analytics/summary`), 지표 계산 `booking/analytics.py`(대시보드 명세 3-1 응답 모양, 방문자는 page_events 전이라 `suppressed`), 로컬 데모 시드 `backend/scripts/seed_demo.py`(SQLite 파일 전용, 팀 DB X), 대시보드 시안(`dashboard/index.html`) 홈이 `?token=`으로 summary API를 불러 숫자 표시
- 공통 파일 변경 (A 승인 필요): `core/db_models.py` import 2줄, `main.py` `booking_tenant_router` 등록 1줄
- 바뀐 계약: 있음(제안) — contracts 2절 상태에 `visited`·`no_show` 추가, 환자가 `proposed`를 거절하면 `cancelled` → **contracts PR 별도로 필요** (결정 19)
- 마이그레이션: 없음 (A에게 요청)
- 테스트: 통과 138개 (`uv run --no-sync python -m pytest backend/tests`, 새 `test_booking_tenant.py` 13개: 전이·이벤트 기록·409·중복·환자 격리·병원 격리 404·환자 토큰 403·summary 기간·다른 병원 제외)
- 다음 할 일: contracts PR(상태 2개) → backend로 PR, 2단계(`tenant_settings`·설정 API)
- A에게 요청:
  1. `tenants`·`staff_users`·`booking_requests`·`booking_events`·`replies` 마이그레이션 리비전 생성 (모델: `modules/tenant/models.py`, `modules/booking/models.py`, Supabase RLS 켜기). `hospitals`가 아직 없어 `hospital_id`는 FK 없이 둠
  2. 직원 로그인 `POST /auth/staff/login` (`staff_users.password_hash` argon2id, 이메일 소문자)
  3. 환자용 `router_patient.py`에서 `booking.service.create_request`·`list_for_patient`·`get_for_patient`·`patient_accept`·`patient_cancel(reason)` 연결, `chatbot/bookings.py`도 `list_for_patient`로
  4. `notification.service.notify()`·`consent.service.require()` 생기면 알려주기 (service.py TODO)
- 막힌 것·질문: 이 PC는 스마트 앱 컨트롤 때문에 `uvicorn.exe`가 막힘 → `python -m uvicorn`으로 실행. 팀 Supabase에는 테이블이 없어 로컬 SQLite(`data/dev/`, git 제외)로 확인함. contracts의 "환자 취소는 pending·proposed에서만"은 그대로 둠 → 확정 뒤 취소는 지금 불가(대시보드 취소율 = 기간 내 취소 ÷ 확정)

### 2026-10-30 · backend · —
- 한 일: worklog 파일 생성 (아직 코드 작업 없음)
- 다음 할 일: contracts 초안 같이 확정, `docker-compose.yml`·`core/db.py`·Alembic 첫 마이그레이션
- A에게 요청: 없음
