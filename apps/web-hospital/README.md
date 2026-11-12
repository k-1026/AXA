# web-hospital · 병원용 화면 (프로토타입)

지금은 **통계 대시보드 1페이지**만 있음 (`src/features/analytics`). 기획: `research/의료관광/병원-대시보드-구성안.md`

## 실행

```bash
npm install
npm run dev   # http://localhost:5175
```

## 화면

- 탭 4개: 홈 · 유입·관심 · 상담·예약 · 사후관리 (주소 `#home` `#inflow` `#booking` `#aftercare`)
- 위쪽 버튼으로 **초기 (데이터 없음)** ↔ **운영 후 (예시)** 전환, 진료과(피부과·내과·안과) 전환
- 카드 배지: `설정` 병원이 채우는 것 · `공공` 실제 공공데이터 · `예시` 가짜 운영 데이터 · `집계 전` 쌓이면 채워짐

## 데이터

- 공공 카드: `public/data/dashboard-public.json` (커밋함)
  - 만드는 스크립트: `data/etl/build_dashboard_public.py` (원본은 `research-data` 브랜치의 `data/`)
  - 다시 만들기: 저장소 루트에서 `python3 -I data/etl/build_dashboard_public.py`
- 예시 병원·운영 숫자: `src/features/analytics/sample.ts` (가상. 실제 병원·환자 아님)
