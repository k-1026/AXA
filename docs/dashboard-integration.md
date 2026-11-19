# dashboard-integration.md — 병원 대시보드 연결 명세 (초안)

> 작성 2026-11-12 · 상태: **팀 검토 전 초안**
> 대상: `apps/web-hospital` (병원 대시보드), `apps/web-platform` (환자 사이트), `backend`
> 기준 문서: [backend-plan.md](backend-plan.md) v2, [backend-contracts.md](backend-contracts.md), [subscription-plans.md](subscription-plans.md)
> 기획: `research/의료관광/병원-대시보드-구성안.md` (research-data 브랜치)
> 이 문서는 **기존 문서에 없는 것만** 추가·변경 제안. 기존 테이블·API는 이름만 참조

## 0. 한 줄 요약

화면은 `apps/web-hospital`에 프로토타입이 있음 (예시 데이터). 백엔드가 이 문서의 API를 같은 모양으로 주면, 프론트는 `src/features/analytics/sample.ts`를 API 호출로 바꾸기만 하면 됨

### 프로토타입 보기

```bash
cd apps/web-hospital && npm install && npm run dev   # http://localhost:5175
```

- 위쪽 버튼: **초기 (데이터 없음)** ↔ **운영 후 (예시)**, 진료과 전환
- 탭 4개: 홈 `#home` · 유입·관심 `#inflow` · 상담·예약 `#booking` · 사후관리 `#aftercare`
- 카드 종류: `설정`(병원 입력) · `공공`(공공데이터) · `예시`(→ 이 문서의 API로 교체) · `집계 전`(데이터 부족 시)

## 1. 지표 → 데이터 출처

상태: ✅ 기존 계획 테이블로 계산 가능 · 🆕 새 테이블·칸 필요 · 📄 정적 파일

### 1-1. 홈

| 카드 | 계산 | 출처 | 상태 |
|---|---|---|---|
| 상세페이지 방문자 | 기간 내 `page_events.type='view'` 고유 방문자 수 | `page_events` | 🆕 |
| 상담 신청 | 기간 내 생성된 `booking_requests` 수 | `booking_requests` | ✅ |
| 예약 확정 | 기간 내 `booking_events`에서 `→ confirmed` 수 | `booking_events` | ✅ |
| 방문 완료 | 기간 내 `→ visited` 수 | `booking_events` | 🆕 상태 추가 (4-1) |
| 취소율 | `→ cancelled` ÷ 확정 수 | `booking_events` | ✅ |
| 지난 기간 대비 | 같은 길이의 직전 기간과 비교 | 위와 같음 | ✅ |
| 오늘 할 일 | 새 요청(`pending`), 오늘 방문 예정(`confirmed`, 확정 시간 = 오늘), 미답변(승인된 답장 없는 `pending`) | `booking_requests`, `replies` | ✅ |
| 병원 정보 등록 n/7 | 7개 설정 항목 채움 여부 | `hospitals`, `hospital_hours`, `tenants`, `tenant_settings`, `availability` | 🆕 `tenant_settings` |
| 등록 유치의료기관·등록번호 | `tenants.등록번호` | `tenants` | ✅ |
| 대구 외국인환자·방문자 추이 | 공공 통계 | `public/data/dashboard-public.json` | 📄 |

### 1-2. 유입·관심

| 카드 | 계산 | 출처 | 상태 |
|---|---|---|---|
| 채널별 홍보 링크 | 병원이 만든 링크 목록 | `promo_links` | 🆕 |
| 경로별 방문 → 상담 → 예약 | `page_events.channel`별 방문, 같은 방문 세션에서 이어진 요청·확정 | `page_events`, `booking_requests.channel` | 🆕 |
| 언어별 상담·예약 | `booking_requests.요청 언어`별 요청·확정 수 | `booking_requests` | ✅ |
| 진료항목별 조회 → 상담 | 상세 화면 시술 카드 조회(`page_events.type='treatment_view'`) vs 요청서 진료항목 | `page_events`, `booking_requests` | 🆕 요청서에 `treatment` 칸 |
| 상세페이지에서 누른 버튼 | `page_events.type='click'`, `target` 별 | `page_events` | 🆕 |
| 자주 묻는 방문 전 질문 | 요청서·답장 주제 태그 집계 | `booking_requests.topic_tags` | 🆕 (처음엔 직원이 태그 선택) |
| 공공 카드 (국적·진료과·성장 여지·거주 외국인·구별 방문자·자주 찾는 시술) | 공공 통계 | `dashboard-public.json` | 📄 |

### 1-3. 상담·예약

| 카드 | 계산 | 출처 | 상태 |
|---|---|---|---|
| 예약 가능 요일·시간 | 설정 | `availability` | ✅ |
| 자주 묻는 질문 | 설정 (언어별) | `tenant_settings.faq` | 🆕 |
| 단계별 전환 | 조회 → 요청 → (`proposed`) → `confirmed` → `visited` | `page_events`, `booking_events` | 🆕 일부 |
| 첫 답변 소요 시간 | 요청 생성 → **첫 승인 답장 발송 시각** (또는 첫 상태 변경 시각 중 빠른 것). **상담 가능 시간 밖은 빼고** 계산 | `booking_requests`, `replies`, `booking_events`, `tenant_settings.consult_hours` | ✅ + 🆕 상담 시간 |
| 취소·변경 사유 | 환자가 취소·변경할 때 고른 사유 코드 | `booking_events.reason` | 🆕 |
| 반복 변경 건수 | 요청 1건당 `proposed`·변경 이벤트 2회 이상 | `booking_events` | ✅ |
| 희망 요일과 확정률 | 희망 날짜 후보의 첫 번째 요일별 요청 수, 그중 확정 비율 | `booking_requests`, `booking_events` | ✅ |
| 대구 같은 진료과 진료시간·비급여 가격 분포 | 공공 | `hospital_hours`, `price_stats` (또는 `dashboard-public.json`) | ✅ / 📄 |

### 1-4. 사후관리

| 카드 | 계산 | 출처 | 상태 |
|---|---|---|---|
| 방문 후 안내문·체크리스트 | 설정 (언어별), `visited` 되면 환자에게 표시 | `tenant_settings.aftercare_guide` | 🆕 |
| 처리 현황 | 사후관리 문의 상태별 수 | `aftercare_threads` | 🆕 (6절 결정 필요) |
| 반복 키워드·주제별 추이 | 문의 태그 집계, 지난달 대비 | `aftercare_threads.tags` | 🆕 (처음엔 직원 태그) |
| 대표 사례 | 태그별 최근 1건, **이름·연락처·사진 가림** 요약 | `aftercare_threads` | 🆕 |
| 개선 기록 | 안내문·FAQ 수정 이력 + 수정 전후 30일 관련 태그 수 | `settings_history` | 🆕 |
| 만족도 | 방문 완료 후 1~5점 (선택), 병원 내부용만 | `satisfaction` | 🆕 |

## 2. 새 테이블·칸

### 2-1. 새 테이블

| 테이블 | 칸 | 규칙 |
|---|---|---|
| `page_events` | id, hospital_id, type(`view`/`click`/`treatment_view`), target(버튼 코드·시술 코드), channel(링크 코드, 없으면 `direct`), lang, visitor_key(브라우저 무작위 값, **하루마다 바뀜**), created_at | **개인정보 없음**: patient_id·IP·기기 정보 저장 X. 로그인 여부와 무관 |
| `promo_links` | id, tenant_id, channel_name, code(짧은 무작위), created_at, disabled_at | 링크: `/hospitals/{id}?ch={code}` |
| `tenant_settings` | tenant_id, interpreter_langs[], consult_hours(요일별), faq[{q,a,lang}], price_note[{item, min, max, lang}], aftercare_guide[{item, lang}], updated_at | 저장할 때마다 `settings_history`에 이전 값 |
| `settings_history` | tenant_id, field, before, after, staff_id, changed_at | 개선 기록 카드용. 지우지 않음 |
| `aftercare_threads` | id, request_id, tenant_id, status(`new`/`unanswered`/`in_progress`/`resolved`), tags[], created_at, resolved_at | 메시지 본문 저장 방식은 6절 결정 후 |
| `satisfaction` | request_id, score(1~5), created_at | **환자 화면에 공개 X** (치료경험담 광고 유형). 병원·운영자만 |

### 2-2. 기존 테이블에 추가할 칸

| 테이블 | 추가 칸 | 이유 |
|---|---|---|
| `booking_requests` | `channel`(링크 코드), `treatment`(진료항목 코드), `topic_tags[]` | 유입 경로·진료항목별 지표 |
| `booking_events` | `reason`(`schedule`/`cost`/`interpreter`/`transport`/`other_hospital`/`other`/`none`) | 취소·변경 사유 |

### 2-3. 상태 추가

```
confirmed ──(병원) 방문 완료 처리──▶ visited
confirmed ──(병원) 미방문 처리────▶ no_show
```

- 환자 사이트의 예약 관리·사후관리 화면은 이미 "방문 완료" 상태를 씀 (현재 예시 데이터)
- [backend-contracts.md](backend-contracts.md) 2절 상태 코드에 `visited`, `no_show` 추가 제안 → **백엔드 B 확인 필요**

## 3. API

모든 경로 앞 `/api/v1`. 병원용은 직원 토큰(`role: staff`)의 `tenant_id`로 자동 필터 ([backend-plan.md](backend-plan.md) 8절)

### 3-1. 병원용 · 통계 (구독 확장 플랜)

| 메서드·경로 | 응답 | 교체되는 프로토타입 값 (`sample.ts`) |
|---|---|---|
| `GET /tenant/analytics/summary?from=&to=` | `{ kpi: [...], today: {...} }` | `KPI`, `TODAY` |
| `GET /tenant/analytics/inflow?from=&to=` | `{ channels, languages, treatments, buttons, preVisitTopics }` | `CHANNELS`, `LANGUAGES`, `TREATMENTS`, `BUTTONS`, `PRE_VISIT_QUESTIONS` |
| `GET /tenant/analytics/booking?from=&to=` | `{ funnel, firstReply, cancelReasons, repeatChanges, preferredDays }` | `FUNNEL`, `FIRST_REPLY`, `CANCEL_REASONS`, `REPEAT_CHANGES`, `PREFERRED_DAYS` |
| `GET /tenant/analytics/aftercare?from=&to=` | `{ status, keywords, sampleCase, improvements, satisfaction }` | `AFTERCARE_*`, `IMPROVEMENTS`, `SATISFACTION` |

응답 예시 (`summary`). 다른 응답도 `sample.ts`의 같은 이름 상수와 **칸 이름·모양을 똑같이** 맞춤

```json
{
  "period": { "from": "2026-11-01", "to": "2026-11-30", "prevFrom": "2026-10-01", "prevTo": "2026-10-31" },
  "kpi": [
    { "key": "views", "now": 1240, "prev": 1051, "unit": "count" },
    { "key": "requests", "now": 86, "prev": 79, "unit": "count" },
    { "key": "confirmed", "now": 31, "prev": 33, "unit": "count" },
    { "key": "visited", "now": 24, "prev": 23, "unit": "count" },
    { "key": "cancelRate", "now": 12, "prev": 9, "unit": "percent", "lowerIsBetter": true }
  ],
  "today": { "newRequests": 5, "bookingRequests": 3, "visitsToday": 2, "unanswered": 4 },
  "suppressed": []
}
```

- 값은 **코드만** (`key`, `unit`), 화면 글자는 프론트 ([backend-plan.md](backend-plan.md) 8절 "값은 코드, 글자는 프론트")
- `suppressed`: 소표본이라 숨긴 칸 목록 (5-2)

### 3-2. 병원용 · 설정

| 메서드·경로 | 하는 일 |
|---|---|
| `GET /tenant/setup-status` | 7개 항목 채움 여부 `[{ key, done, source }]` (`hours`·`homepage`는 공공 데이터에서 불러옴 표시) |
| `GET·PUT /tenant/settings` | 통역 언어, 상담 가능 시간, FAQ, 가격 안내, 방문 후 안내문 |
| `GET·PUT /tenant/availability` | (기존) 예약 가능 요일·시간 |
| `GET·POST·DELETE /tenant/promo-links` | 홍보 링크 만들기·끄기 |
| `POST /tenant/booking-requests/{id}/visited` · `/no-show` | 방문 완료·미방문 처리 (2-3) |
| `GET /tenant/aftercare` · `PATCH /tenant/aftercare/{id}` | 사후관리 문의 목록, 상태·태그 변경 |

### 3-3. 환자용 (`apps/web-platform`)

| 메서드·경로 | 로그인 | 하는 일 | 주의 |
|---|---|---|---|
| `POST /events` | X | `{ hospitalId, type, target?, channel?, lang, visitorKey }` 기록 | 요청 횟수 제한, 응답 기다리지 않음 (`sendBeacon`) |
| `GET /hospitals/{id}` | X | (기존) + `settings` 중 공개 항목 (통역 언어, FAQ, 가격 안내, 등록 유치의료기관 여부) | 구독 여부로 노출·정렬 차이 X |
| `POST /me/booking-requests/{id}/cancel` | O | (기존) + `reason` 받음 | 사유는 선택 |
| `POST /me/booking-requests/{id}/satisfaction` | O | `visited` 후 1회 | 공개 X |

### 3-4. 공공 카드

- 지금: `apps/web-hospital/public/data/dashboard-public.json` (스크립트 `data/etl/build_dashboard_public.py`, research-data 브랜치)
- 나중에 옮길 수 있음: 진료시간 분포는 `hospital_hours`, 가격은 `price_stats`에서 계산하는 `GET /public/daegu-stats`. 통계 보고서·법무부·관광공사 값은 파일 유지로 충분 **(제안)**

## 4. 프론트 할 일

### 4-1. `apps/web-hospital`

| 할 일 | 내용 |
|---|---|
| 직원 로그인 화면 | `POST /auth/staff/login` → 토큰 보관 → 대시보드 |
| API 연결 | `sample.ts` 상수 → 3-1 API 호출. 기간 선택(이번 달·지난달·직접) 추가 |
| 초기/운영 전환 버튼 제거 | 실제 데이터로 판단: 칸마다 `suppressed`이면 "집계 전" 카드 |
| 설정 저장 | 홈 "입력하기", 예약 요일, FAQ, 안내문, 홍보 링크 → 3-2 API |
| 플랜 확인 | 확장 플랜이 아니면 통계 탭 대신 안내 (6절) |

### 4-2. `apps/web-platform`

| 할 일 | 내용 |
|---|---|
| 이벤트 기록 | 병원 상세 진입(`view`), 버튼(`call`/`homepage`/`consult`/`directions`/`favorite`), 시술 카드(`treatment_view`) |
| 홍보 링크 | 주소의 `?ch=` 값을 그 방문 동안 유지 → 이벤트·요청서에 같이 보냄 |
| 취소·변경 사유 | 예약 관리 화면의 취소 확인에 사유 선택 칸 (선택 사항) |
| 병원 설정 표시 | 병원 상세에 통역 언어, FAQ, 가격 안내, 등록 유치의료기관 표시 |
| 만족도 | 방문 완료 예약에 1~5점 (선택), "병원에만 전달되고 공개되지 않아요" 안내 |

## 5. 규칙

### 5-1. 데이터 격리·권한

- 병원용 API는 전부 `current_staff()`의 `tenant_id`로만 조회 ([backend-contracts.md](backend-contracts.md) 3절)
- 다른 병원 숫자는 **어떤 형태로도** 주지 않음. 비교는 공공데이터의 대구 전체 분포만

### 5-2. 소표본 숨김 (서버에서)

| 대상 | 기준 **(팀 판단값, 법적 근거 아님)** | 처리 |
|---|---|---|
| 국적·언어별 칸 | 5명 미만 | 값 대신 `null` + `suppressed`에 칸 이름 → 화면 "5 미만" |
| 조회·클릭 | 월 30회 미만 | 카드 전체 "집계 전" |
| 대표 사례 | 같은 태그 3건 미만 | 사례 안 보여줌 (개인 특정 방지) |

- 화면에서만 숨기면 응답에 값이 그대로 있음 → **반드시 서버에서**

### 5-3. 개인정보

| 항목 | 규칙 |
|---|---|
| `page_events` | 개인 식별 정보 없음. `visitor_key`는 하루마다 바뀌는 무작위 값 |
| 사후관리·요청서 내용 | 건강정보 → 해당 병원 직원만, 열람 기록 (`audit_logs`) |
| 대표 사례 | 국적·연령대·방문월만, 이름·연락처·사진·날짜 상세 X |
| AI 요약·태그 | [backend-plan.md](backend-plan.md) 8절 "LLM 전 마스킹" 적용 |
| 보관 기간 | `page_events`는 집계 후 원본 삭제 기간 정함 (제안: 13개월, 전년 같은 달 비교용). 요청서는 기존 결정(질의 회신 후) 따름 |

### 5-4. 의료광고·요금

- 만족도·후기는 환자 화면에 공개 X (의료법 제56조 제2항 제2호 유형, `웹사이트-법적-점검.md`)
- 통계는 구독 확장 플랜 기능. 요금은 예약·환자 수와 연동 X ([subscription-plans.md](subscription-plans.md))
- 구독 여부는 환자 화면 노출·정렬에 영향 X

## 6. 팀이 정할 것

| 항목 | 선택지 | 제안 | 관련 |
|---|---|---|---|
| **상담 방식** | (A) 요청서 단위 답장만 ([backend-plan.md](backend-plan.md) 6절) / (B) 병원별 대화 (환자 사이트 현재 화면) | 시연은 B 화면 유지, 저장은 A 구조(요청서에 딸린 메시지)로 → 지표 계산 같음 | 첫 답변 시간, 사후관리 |
| **사후관리 저장** | 요청서(`visited`)에 딸린 메시지 / 별도 대화 | 요청서에 딸린 메시지 + `aftercare_threads`는 상태·태그만 | 1-4 |
| `visited`·`no_show` 상태 | 추가 / 별도 칸 | 상태 추가 (2-3) | 홈 KPI |
| 소표본 기준 | 5명·30회·3건 | 표대로 시작, 시연 후 조정 | 5-2 |
| 공공 카드 위치 | 정적 파일 / API | 정적 파일 유지 | 3-4 |
| 확장 플랜 아닌 병원 | 통계 탭 숨김 / 공공 카드만 보여줌 | 공공 카드 + 설정은 모두에게, 운영 통계만 확장 플랜 | 4-1 |
| 태그 분류 | 직원 수동 / AI | 수동으로 시작, AI는 `agent` 단계 이후 | 1-2, 1-4 |

## 7. 작업 순서 (제안)

| 단계 | 백엔드 | 프론트 | 완료 기준 |
|---|---|---|---|
| 1. 예약 지표 | `visited` 상태, `/tenant/analytics/summary`·`/booking` (기존 테이블로 계산) | 직원 로그인, 홈·상담·예약 탭 API 연결 | 시드 데이터로 홈 KPI·단계별 전환이 실제 계산값 |
| 2. 병원 설정 | `tenant_settings`, `settings_history`, `/tenant/settings`, `/tenant/setup-status` | 설정 저장, 환자 상세에 표시 | 병원이 FAQ 입력 → 환자 상세에 보임 |
| 3. 유입 기록 | `page_events`, `promo_links`, `POST /events`, `/tenant/analytics/inflow` | 이벤트 기록, `?ch=` 유지 | 홍보 링크로 들어온 방문이 경로별 표에 집계 |
| 4. 사후관리 | `aftercare_threads`, `satisfaction`, 취소 사유, `/tenant/analytics/aftercare` | 사후관리·취소 사유·만족도 연결 | 사후관리 탭 처리 현황이 실제 값 |

- 각 단계 끝나면 프로토타입의 해당 `예시` 배지 제거
- 1단계는 [backend-plan.md](backend-plan.md) 10절 일정의 `booking` 작업과 같이 가능

## 8. 변경 이력

| 날짜 | 내용 |
|---|---|
| 2026-11-12 | 초안 |
