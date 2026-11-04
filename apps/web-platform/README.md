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
├── pages/                MainPage(지도+진료과 필터+광고 자리), HospitalsPage(카드 목록), HospitalDetailPage, PriceGuidePage, PlaceholderPage
├── components/           AdSlot, currency(통화 선택 상태), storage(설정 저장)
├── i18n/                 react-i18next, locales/ ko·en·zh-CN·zh-TW·vi
└── features/
    ├── map/              HospitalMap, DepartmentFilter
    ├── hospital/         HospitalCard, FilterGrid, filters(진료과·구군 목록), 타입, useHospitals
    ├── price-info/       가격 가이드 시술 목록·카드
    ├── chatbot/          (예정) 챗봇
    └── booking-request/  (예정) 예약 요청서
scripts/build-hospitals.mjs   지도용 병원 JSON 생성
scripts/romanize.mjs          병원 이름 → 영어 이름
```

## 현재 상태 (2026-11-02)

| 항목 | 상태 |
|---|---|
| 대상 병원 | 피부과·성형외과·내과·안과 1,267곳 (대구 전체 4,242곳 중, 폐업 교차검증에서 폐업·미확인인 곳 제외). 한국어 가나다순 고정 |
| 지도 | 위 병원 표시, 진료과별 색상(피부과 분홍·성형외과 보라·내과 노랑·안과 파랑, 여러 진료과면 이름에 있는 진료과 기준), 마커 클릭 시 종류·주소·전화·출처 |
| 병원 정보 (`/hospitals`) | 진료과·구군 필터(주소에 저장), 카드 24개씩 더 보기. 카드 = 사진 자리·이름·주소·전화·홈페이지·인스타그램·찜 하트 (찜은 이 브라우저에만 저장, 마이페이지 저장한 병원에 표시) |
| 병원 상세 (`/hospitals/:id`) | 진료시간·점심·접수·휴진, 응급실·주차, 위치 지도. **빈 값은 빈칸** |
| 진료과 판정 | 피부과·성형외과 = 심평원 진료과목 코드, **내과·안과 = 임시로 의원·병원 이름에 '내과'·'안과'** (종합병원 내과·안과는 빠짐 → 진료과목 01·12 수집 후 교체) |
| 홈페이지·인스타그램 | 팀 수집 파일을 이름·전화·주소로 맞춘 `data/processed/daegu_hospital_links.csv` 우선, 없으면 심평원 홈페이지. 블로그·네이버는 어느 쪽 값이든 넣지 않음 |
| 방문 기록 (`/mypage/visits`) | 본인만 쓰고 보는 다이어리: 병원·날짜·경험 입력, 수정·삭제. 이 브라우저에만 저장, 공개 후기 아님 (병원 화면에 표시 X, 별점·추천 없음) |
| 병원 사진 | 팀 수집 파일을 요양기관 기호로 맞춘 `data/processed/daegu_hospital_photos.csv`의 외부 주소로 표시 (사진 파일은 저장 안 함). 없거나 못 불러오면 "대표사진 없음" 표시. 방문자·블로그 리뷰 사진은 쓰지 않음 (영수증 등 개인정보 포함). **프로토타입용 임시**: 광고성 이미지 포함, 이용 조건 미확인, 용량이 커서 느림 → 정식 공개 전에 교체 |
| 가격 가이드 (`/prices`) | 진료과 필터, 시술 66개 카드 (`features/price-info/procedures.ts`, 팀 문서 "병원별 시술 모음" 기준). 이름은 한국어 외 언어에서 영어로 통일. 사진은 팀 제작 일러스트 58개 적용, 나머지 8개는 빈 자리 (원본 `assets/medical_illustrations_*`는 git 제외, 축소본 `public/procedures/`). 가격은 피부과 6개만 범위 표시 (`daegu_derm_homepage_price_stats.csv`, 스킨보톡스 외에는 기관 5곳 미만, 프로토타입용 임시 값), 나머지는 "가격 확인 중" |
| 언어 | UI 문구 5개 언어. 병원 이름은 한국어 외 모든 언어에서 영어로 통일: 발음 표기 + 진료과·기관 종류 영어 번역 (`scripts/romanize.mjs`, 음절 단위 로마자 표기법). 주소는 아직 한국어 원문 |
| 통화 | 선택값만 저장. 환산은 가격 가이드에서 (환율 출처 미정) |
| 로그인·광고·나머지 메뉴 | 자리만 있음 |
| 번역 | 중국어·베트남어 문구는 초안 → 원어민·팀원 3 검수 필요 |

## 지킬 것 (docs/compliance.md)
- 지도·목록 정렬에 순위·추천·유료 여부 반영 X
- 광고는 목록·상세 옆에만, 건강·미용 카테고리 차단. 예약 요청서·동의·챗봇 화면엔 X
- 출처·수집일 표시
