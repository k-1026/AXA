# dashboard · 입점 병원 대시보드 (프로토타입)

예전 `apps/web-hospital`(포트 5175)을 환자 사이트에 합침. 주소: **http://localhost:5173/dashboard** (`npm run dev` 하나로)

지금은 **통계 대시보드 1페이지**만 있음 (`features/analytics`). 기획: `research/의료관광/병원-대시보드-구성안.md`

## 합친 방식

- **진입 막기**: 직원 토큰(이 탭 sessionStorage, `features/staff/staffSession.ts`)이 있을 때만 열림. 없으면 로그인 화면의 "병원 관계자"로 (`features/staff/RequireStaff.tsx`). 화면만 막는 것이고 실제 권한은 백엔드가 토큰으로 확인
- **나눠 불러오기**: `main.tsx`에서 `React.lazy`로 불러옴 → 빌드 결과 `DashboardApp-*.js`·`DashboardApp-*.css`가 따로 생기고, 환자 화면에서는 내려받지 않음
- **CSS**: `dashboard.css`의 모든 규칙은 최상위 `.hd` 아래로만 적용 (환자 화면 `src/styles.css`와 클래스 이름이 겹쳐도 섞이지 않게). 새 규칙도 `.hd ` 로 시작할 것
- 환자 사이트 헤더·메뉴(Layout) 없이 따로 그림. 오른쪽 위 "로그아웃"은 직원 토큰만 지움

## 화면

- 탭 4개: 홈 · 유입·관심 · 상담·예약 · 사후관리 (주소 `/dashboard#home` `#inflow` `#booking` `#aftercare`)
- 위쪽 버튼으로 **초기 (데이터 없음)** ↔ **운영 후 (예시)** 전환, 진료과(피부과·내과·안과) 전환
- 카드 배지: `설정` 병원이 채우는 것 · `공공` 실제 공공데이터 · `예시` 가짜 운영 데이터 · `집계 전` 쌓이면 채워짐

## 데이터

- 공공 카드: `data/dashboard-public.json` (커밋함, 대시보드 코드와 같이 묶임)
  - 만드는 스크립트: `data/etl/build_dashboard_public.py` (원본은 `research-data` 브랜치의 `data/`). 다시 만든 파일은 이 위치로 복사
- 예시 병원·운영 숫자: `features/analytics/sample.ts` (가상. 실제 병원·환자 아님)

시연용 대시보드 `dashboard/대시보드.html`은 그대로 따로 있음 (`VITE_DASHBOARD_URL`이 있으면 병원 관계자 로그인 뒤 그쪽으로 이동)
