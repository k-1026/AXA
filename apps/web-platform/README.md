# web-platform — 환자용 정보 웹 (MediDaegu)

React + TypeScript (Vite). 지도는 Leaflet + OpenStreetMap (API 키 필요 없음).

## 실행

```bash
cd apps/web-platform
npm install
npm run dev        # http://localhost:5173
```

`npm run dev`·`npm run build` 전에 `scripts/build-hospitals.mjs`가 자동으로 돌아서
`data/interim/영업정보/daegu_hospital_hours.csv` → `public/data/hospitals.json`을 만든다 (git에는 안 올림).

## 구조

```
src/
├── main.tsx              라우트 (메인·병원 정보·가격 가이드·챗봇·서비스 소개·로그인)
├── layout/               Header(언어·통화·로그인) · Sidebar(메뉴) · Footer(고지·출처)
├── pages/                MainPage(지도+진료과 필터+광고 자리), PlaceholderPage(준비 중 화면)
├── components/           AdSlot, currency(통화 선택 상태), storage(설정 저장)
├── i18n/                 react-i18next, locales/ ko·en·zh-CN·zh-TW·vi
└── features/
    ├── map/              HospitalMap, DepartmentFilter, departments(필터 목록)
    ├── hospital/         병원 타입, useHospitals(데이터 불러오기)
    ├── price-info/       (예정) 가격 가이드
    ├── chatbot/          (예정) 챗봇
    └── booking-request/  (예정) 예약 요청서
scripts/build-hospitals.mjs   지도용 병원 JSON 생성
```

## 현재 상태 (2026-10-30)

| 항목 | 상태 |
|---|---|
| 지도 | 심평원 대구 병원 4,242곳 표시, 마커 클릭 시 종류·주소·전화·출처 |
| 진료과 필터 | 피부과·성형외과(심평원 진료과목), 치과(종별 치과병원·치과의원). **내과는 진료과목 데이터가 없어 "준비 중"** |
| 언어 | UI 문구만 5개 언어. 병원 이름·주소는 아직 한국어 원문 |
| 통화 | 선택값만 저장. 환산은 가격 가이드에서 (환율 출처 미정) |
| 로그인·광고·나머지 메뉴 | 자리만 있음 |
| 번역 | 중국어·베트남어 문구는 초안 → 원어민·팀원 3 검수 필요 |

## 지킬 것 (docs/compliance.md)
- 지도·목록 정렬에 순위·추천·유료 여부 반영 X
- 광고는 목록·상세 옆에만, 건강·미용 카테고리 차단. 예약 요청서·동의·챗봇 화면엔 X
- 출처·수집일 표시
