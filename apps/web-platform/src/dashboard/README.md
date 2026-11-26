# dashboard · 입점 병원 대시보드

예전에 따로 띄우던 대시보드 2개(포트 5175)를 환자 사이트에 합침. `npm run dev` 하나로 5173에서 열림

| 주소 | 화면 | 예전 위치 |
|---|---|---|
| http://localhost:5173/dashboard | **메인 대시보드** (탭 4개: 홈·유입·관심·상담·예약·사후관리, 지금은 예시 데이터) | `apps/web-hospital` → 예전 `/dashboard/analytics` |
| http://localhost:5173/dashboard/legacy | 옛 대시보드 **보관용** (상담 답장·예약 확정·사후관리 채팅·결제 확인·요금·병원 설정, 백엔드 연결). 메뉴에 없고 주소로만 열림 | `dashboard/대시보드.html` → 예전 `/dashboard` |

- 예전 주소 `/dashboard/analytics#탭`은 `/dashboard#탭`으로 넘어감
- **대시보드 개편 중 (브랜치 `frontend-dashboard-redesign`)**: 메인 화면 틀은 `AnalyticsApp.tsx`. 옛 화면의 백엔드 연결 기능을 React 탭으로 하나씩 옮기고, 다 옮기면 `DashboardPage.tsx`·`demo/`와 `/dashboard/legacy` 주소를 삭제

## 합친 방식

- **진입 막기**: 두 주소 모두 직원 토큰(이 탭 sessionStorage, `features/staff/staffSession.ts`)이 있을 때만 열림. 없으면 로그인 화면의 "병원 관계자"로 (`features/staff/RequireStaff.tsx`). 화면만 막는 것이고 실제 권한은 백엔드가 토큰으로 확인
  - 환자 사이트 "병원 관계자 로그인" → 토큰 저장 → `/dashboard`. 대시보드의 로그아웃·만료(401)는 토큰을 지우고 로그인 화면으로
- **나눠 불러오기**: `main.tsx`에서 `React.lazy`로 불러옴 → 빌드 결과 `DashboardPage-*.js/css`, `AnalyticsApp-*.js/css`가 따로 생기고 환자 화면에서는 안 내려받음
- **CSS**: 대시보드는 최상위 `.md-dashboard`, 통계 상세는 `.hd` 아래로만 규칙이 적용됨 (환자 화면 `src/styles.css`와 클래스·태그 이름이 겹쳐도 섞이지 않게). 새 규칙도 이 접두사로 시작할 것
- 둘 다 환자 사이트 헤더·메뉴(Layout) 없이 따로 그림

## 파일

```
DashboardPage.tsx      /dashboard/legacy (보관용) — markup.html을 넣고 legacy.js를 시작·정리
demo/markup.html       화면 틀 (예전 대시보드.html의 <body>)
demo/legacy.js         동작 (예전 <script> 그대로, startDashboard(host, { onLeave })로 감쌈)
demo/demo.css          스타일 (예전 <style>, .md-dashboard 범위)
AnalyticsApp.tsx       /dashboard (메인)
analytics.css          .hd 범위
features/analytics/    통계 탭·카드, sample.ts(가상 병원·운영 숫자)
data/dashboard-public.json  공공 카드 (data/etl/build_dashboard_public.py, research-data 브랜치) — 다시 만들면 이 위치로 복사
```

- `legacy.js`는 `document.getElementById`로 찾으므로 한 화면에 하나만 띄움. 다이얼로그·알림은 `.md-dashboard` 안에 붙음
- API 주소는 환자 사이트와 같음 (`VITE_API_URL`, 기본 `http://localhost:8000`)
