# 내 할 일 (백엔드 A · 2026-11-16 ~ )

> 전제: 병원 대시보드 API는 다른 팀원이 `docs/dashboard-integration.md` 명세로 만든다. 나는 **환자 쪽 백엔드(A) + compliance.md 정리**를 맡는다
> 근거: `docs/backend-todo-A.md`, `docs/backend-worklog-A.md`(11/12), `research/의료관광/법률점검-약관-처리방침-2026-11-12.md`, `subject/subject.md`(11/10 방향)

## 전체 순서 (2026-11-16 기준)

| # | 할 일 | 상태 |
|---|---|---|
| 1 | compliance.md v2 + subscription-plans·agent-spec·공용 3파일 수정 (`docs-compliance-v2` 브랜치) | ✅ 작성 (커밋 전) |
| 2 | 팀에 [공지](공용파일-변경-공지-2026-11-16.md) → 커밋·push → main PR | 다음 |
| 3 | 백엔드 A 1~2번 (병원 데이터 API, 챗봇 카드 id) — 아래 1절 | 2와 동시에 시작 가능 |
| 4 | B와 맞추기 (2절) — 요청서 API 전에 `booking_requests` 테이블·계약 승인 | 3 진행 중 |
| 5 | 백엔드 A 3~4번 (요청서 제출·내 요청) — compliance 2-2·2-4·2-6 반영 | 4 뒤 |
| 6 | 백엔드 A 5~6번 (동의 버전, Cron) | 틈틈이 |

## 0. compliance.md 정리

- 대조표: [compliance-대조-2026-11-16.md](compliance-대조-2026-11-16.md). 팀 결정 D1~D4는 2026-11-16에 추천안대로 정함 → [compliance.md](compliance.md) v2에 반영
- 프론트·B·AI에 넘길 일은 [공지](공용파일-변경-공지-2026-11-16.md) "구현 담당에게 넘기는 것"

## 1. 백엔드 A — 순서대로

| 순서 | 할 일 | 왜 지금 | 막히는 것 |
|---|---|---|---|
| 1 | **병원 데이터**: `hospitals`·`hospital_hours`·`hospital_departments` 테이블 + `scripts/load_hospitals.py`(4,242곳) + `GET /hospitals`(필터, 정렬은 거리·이름만) + `GET /hospitals/{id}` + `hospital.service.get_basic()` | 대시보드·예약·챗봇 병원 카드가 모두 이 위에 올라감 | 데이터 담당과 CSV 최신본 확인 |
| 2 | 챗봇 카드 `hospital_id`(데모 숫자) ↔ 사이트 병원 id(ykiho) 맞추기 | 1번 끝나면 바로 가능 | — |
| 3 | **요청서 제출**: `POST /hospitals/{id}/booking-requests` — 동의 4개 확인(compliance 2-4), 국내 거주 재확인(compliance 2-2), 공개 환경 제출 차단(2-6), `channel`·`treatment` 칸은 **처음부터** 넣기(대시보드 명세 2-2) | 시연 핵심 흐름 | B의 `booking_requests`·`booking.service.create_request()` |
| 4 | `GET /me/booking-requests`·`/{id}`, `accept`·`cancel`(+`reason`) | 마이페이지·챗봇 연결 | 3번 |
| 5 | 동의 문서 버전: health·overseas_transfer에도 버전 기록 (`consent/service.py`) | 법률점검 1장 7번 | — |
| 6 | worklog 11/12 남은 것: Vercel Cron(`vercel.json`), 챗봇 `state` 동시 저장 충돌 | 30일 삭제 약속 이행 | Vercel IP 확인 |

## 2. B·대시보드 담당과 맞출 것

| 상대 | 내용 |
|---|---|
| B | 계약 1·4·5·6·7절 변경 승인, PK 이름 정리 마이그레이션, `staff_users` 생기면 `/auth/staff/login` 같이 |
| B | 확정 후 환자 취소 허용 여부, `visited`·`no_show` 상태 추가 (대시보드 취소율·방문 완료 지표가 달림) |
| 대시보드 담당 | 내가 줄 것: `hospital.service.get_basic()`, `booking_requests.channel`·`treatment` 칸. 사후관리 탭은 compliance 1절 기준(2027-05 전 비의료 문의만) |

## 3. 하지 않는 것 (다른 사람 담당)

- 병원 대시보드 API·`tenant_settings`·`page_events` (대시보드 담당)
- 예약 상태 흐름·병원 계정 (B)
