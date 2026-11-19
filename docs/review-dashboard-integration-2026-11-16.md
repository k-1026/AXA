# 병원 대시보드 연결 명세 검토 (2026-11-16)

- 대상: `origin/docs-dashboard-integration`의 `docs/dashboard-integration.md` (11/12 초안) + `apps/web-hospital` 프로토타입
- 비교 기준: `origin/main`의 `backend-contracts.md`, `backend-plan.md`, `subscription-plans.md`, `compliance.md`, 실제 `backend/` 코드·마이그레이션
- 결론: **지표 정의·개인정보·소표본 규칙은 잘 잡혀 있음.** 다만 "✅ 기존 테이블로 계산 가능"이라고 한 테이블이 **아직 하나도 없음**, 요금·사후관리 방향이 옛 문서 기준이라 API 착수 전에 아래 1~3번을 먼저 정해야 함

## 1. 착수 전에 꼭 정할 것

| # | 문제 | 근거 | 제안 |
|---|---|---|---|
| 1 | ✅로 표시한 테이블(`hospitals`, `tenants`, `staff_users`, `booking_requests`, `booking_events`, `replies`, `availability`, `audit_logs`)이 **계획에만 있고 DB에 없음**. 지금 마이그레이션은 0001~0005(환자·동의·환율·챗봇 대화)뿐, 모듈도 auth·chatbot·consent·fx·patient만 있음 | `backend/alembic/versions/`, `backend/src/modules/` | 명세 7절 1단계 앞에 **0단계: 병원·테넌트·직원·예약 기반** 추가. 대시보드 API는 0단계 뒤 |
| 2 | "통계 = 구독 확장 플랜", "요금은 예약 건수와 연동 X"는 **옛 요금 방향**. 11/12 발표자료는 수수료·구독 둘 다 주 요금제(병원 선택), CLAUDE.md는 건당 중개수수료 | `subscription-plans.md` 7·16행, 발표자료 5·6장 | 수수료 플랜 병원에게 통계를 보여 줄지 팀 결정 → `subscription-plans.md` 먼저 갱신 |
| 3 | 사후관리 탭(`aftercare_threads`, 방문 후 안내문)이 `compliance.md`의 "하지 않는 것: 사후관리 Q&A, 시술 후 의료 안내 메시지"와 충돌. 새 방향(11/10)은 사후관리를 핵심 기능으로 넣음 | `compliance.md` 14행, CLAUDE.md | `compliance.md`를 새 방향으로 고칠지 먼저 결정. 그 전까지 명세 4단계(사후관리)는 보류 |

## 2. 계약과 어긋나는 부분

| # | 문제 | 제안 |
|---|---|---|
| 4 | **취소율 = `cancelled` ÷ 확정 수**인데, 계약상 환자 취소는 `pending`·`proposed`에서만 가능 → 확정 뒤 취소가 없어서 분자와 분모가 다른 집단 | 확정 후 취소를 허용할지 B와 결정. 아니면 취소율 = 취소 ÷ 요청 |
| 5 | `visited`·`no_show` 상태 추가 = 계약 2절 변경 → **B 승인 필요**. 환자 프론트는 지금 "확정 + 방문 시각 지남 = visited"로 화면에서만 계산 | 상태 추가에 동의하면 프론트 `displayStatus()`도 서버 값으로 바꾸기 |
| 6 | 응답 예시가 camelCase(`prevFrom`, `lowerIsBetter`, `newRequests`)인데, 기존 API는 snake_case(`hospital_id` 등) | 백엔드 규칙(snake_case)으로 맞추고 프론트에서 변환, 또는 명세에 예외라고 명시 |
| 7 | `booking_requests`에 `channel`·`treatment`·`topic_tags` 추가 제안 | 요청서 API(A)를 만들 때 **처음부터 칸을 넣으면** 마이그레이션 1번으로 끝남 |
| 8 | 직원 로그인 `POST /auth/staff/login`은 B의 `staff_users`가 생긴 뒤 가능 (`auth/service.py` 주석) | 0단계에 포함 |

## 3. 빠진 파일·확인할 것

| # | 내용 |
|---|---|
| 9 | 공공 카드 스크립트 `data/etl/build_dashboard_public.py`가 **research-data·main 어느 쪽에도 없음** (JSON 결과만 `apps/web-hospital/public/data/`에 있음) → 작성자에게 올려 달라고 요청 |
| 10 | `page_events`의 `visitor_key`(브라우저 저장 무작위 값)는 개인정보는 아니지만 쿠키·저장소 고지가 필요한지 **미확인** |
| 11 | 프로토타입 `package-lock.json`이 새로 생김 → `apps/web-platform`과 같은 Node·Vite 버전인지 확인 |

## 4. 잘 된 점 (그대로 유지)

- 지표마다 계산식·출처 테이블이 있어 API 모양을 바로 정할 수 있음
- 소표본 숨김을 **서버에서** 하도록 명시 (5-2)
- `page_events`에 patient_id·IP 저장 X, 만족도 비공개(의료광고 유형) 명시
- 다른 병원 숫자는 어떤 형태로도 주지 않음 (5-1)

## 5. 권장 작업 순서

| 순서 | 할 일 | 담당 | 대시보드와의 관계 |
|---|---|---|---|
| 0 | 팀 결정: 위 1-2(요금·통계 노출), 1-3(사후관리 허용 범위), 2-4·2-5(취소 규칙·`visited`) | 팀 전체 | 명세 확정 조건 |
| 1 | `backend-B-health-404` → `backend` PR, A가 바꾼 계약(1·4·5·6·7절) B 승인 | B | 쌓인 것 정리 |
| 2 | **병원 데이터**: `hospitals`·`hospital_hours` 테이블 + `load_hospitals.py` + `GET /hospitals`, `/hospitals/{id}` | A | 대시보드 모든 지표의 기준 |
| 3 | **테넌트·직원**: `tenants`·`staff_users`·`availability` + `POST /auth/staff/login` | B (로그인은 A와 같이) | 대시보드 로그인·격리 |
| 4 | **예약 흐름**: `booking_requests`(+`channel`·`treatment`)·`booking_events`·`replies` + 요청서 제출(A) + 확정·거절·제안(B) | A·B | 명세 1단계의 데이터 원천 |
| 5 | **명세 1단계**: `visited` 상태, `/tenant/analytics/summary`·`/booking` + 시드 데이터 | 대시보드 담당 | 2~4가 끝나야 실제 값 |
| 6 | 명세 2단계(병원 설정) → 3단계(유입 기록) | 대시보드 담당 + 프론트 | |
| 7 | 명세 4단계(사후관리) — 0번 결정 후 | | |

- 2와 3은 동시에 진행 가능 (테이블이 겹치지 않음). 4는 2·3이 끝난 뒤
- 대시보드 담당은 2~4가 진행되는 동안 **명세 수정(1~3절) + 시드 데이터 + 집계 쿼리 테스트**를 먼저 준비하면 기다리는 시간이 줄어듦
