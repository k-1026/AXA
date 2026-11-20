# SEO 구축 계획 — 메디대구 환자용 웹

> **보류 (2026-11-20 팀 결정)**: SEO는 하지 않고 병원은 직접 찾아가기로 했어요 → [병원-방문영업-플레이북.md](병원-방문영업-플레이북.md). 이 문서는 나중을 위해 남겨 둬요

> 작성 2026-11-20 · 상태: **Claude 초안, 프론트 팀 검토 전** (코드 변경은 프론트 담당 — 이 문서는 계획만)
> 대상: 환자용 웹 `apps/web-platform` (frontend 브랜치). 병원 쪽(B2B)은 SEO를 지금 하지 않음 → [B2B-병원-마케팅.md](B2B-병원-마케팅.md) 3-7
> 관련: [마케팅-유입방법-고안.md](마케팅-유입방법-고안.md) (SNS 쪽 유입) · **쉬운 설명: [SEO-쉽게-설명.md](SEO-쉽게-설명.md)**

## 0. 결론

지금 웹은 **검색엔진이 거의 못 읽는 구조**예요. 먼저 고칠 것은 3가지예요.

1. **언어를 URL로 나누기** — 지금은 브라우저 언어·저장값으로 화면 언어를 바꿔서, 검색엔진에는 한 언어로만 보여요. Google은 언어마다 **다른 URL**을 쓰고 hreflang으로 묶으라고 권해요 [S1]
2. **공개 페이지를 미리 그려 둔 HTML로 내보내기** — 지금은 빈 `<div id="root">`만 내려가고 화면은 브라우저에서 JavaScript로 그려져요. 병원 상세 161곳 등 공개 페이지는 빌드할 때 HTML로 만들어 두기
3. **페이지마다 제목·설명·사이트맵** — 지금은 모든 페이지 제목이 `MediDaegu` 하나, 사이트맵·robots.txt 없음

그다음에 병원·진료과 안내 글(영어 먼저)과 구조화 데이터, 측정 도구를 붙여요.

## 1. 지금 상태 (코드 확인, 2026-11-20)

| 항목 | 지금 | 문제 |
|---|---|---|
| 화면 그리기 | React + Vite, 브라우저에서 그림 (`index.html`에는 `<div id="root">`만) [S5] | 검색엔진이 JavaScript를 실행해야 내용이 보임. 실행하지 않거나 늦게 실행하는 검색엔진·링크 미리보기는 빈 페이지로 봄 [S2] |
| 언어 | `navigator.languages`·저장값으로 자동 선택, URL은 언어와 상관없이 같음 (`/hospitals/123`) [S5] | Google 권장과 반대 — 언어별 URL이 없어 번체·베트남어 페이지가 검색에 따로 잡히지 않음 [S1] |
| `<html lang>` | `ko` 고정 [S5] | 실제 화면 언어와 다름 |
| 페이지 제목·설명 | 모든 페이지 `<title>MediDaegu</title>`, 설명 없음 [S5] | 검색 결과에서 페이지 구분이 안 됨 |
| 주소 구조 | `/`, `/hospitals`, `/hospitals/:id`, `/prices`, `/legal/:slug` 공개 · `/mypage` `/booking` `/chatbot` `/reserve` `/aftercare`는 로그인 필요 [S5] | 공개·비공개 구분은 이미 있음 (좋음) |
| 사이트맵·robots.txt | 없음 (`public/`에 없음) [S5] | 검색엔진에 어떤 페이지가 있는지 알려 주지 못함 |
| 병원 데이터 | `public/data/hospitals.json` (빌드 때 공공데이터로 생성, 등록 기관 161곳) [S5] | **장점**: 정적 데이터라 병원 상세를 미리 HTML로 만들기 쉬움 |

## 2. 단계별 구축

### 1단계 — 검색엔진이 읽을 수 있게 (먼저, 프론트 작업)

| 할 일 | 방법 | 근거 |
|---|---|---|
| **언어별 URL** | `/en/…`, `/zh-tw/…`, `/zh-cn/…`, `/vi/…`, `/ja/…`(배포 후), `/ko/…`. 언어 메뉴는 URL을 바꿈. 첫 방문 `/`는 브라우저 언어로 **안내만** 하고 강제로 넘기지 않기 | Google: 언어마다 다른 URL 권장, 쿠키·브라우저 설정으로 바꾸지 말 것 [S1] |
| **hreflang** | 각 페이지 `<head>`에 모든 언어 버전 + 자기 자신 + `x-default`를 절대 주소로 | 각 버전은 자기 자신 포함 전체 목록을 적어야 하고, 주소는 `https://`부터 전체로 [S1] |
| **공개 페이지 미리 그리기 (SSG)** | 빌드할 때 공개 페이지(홈·병원 목록·병원 상세 161곳·가격 가이드·법적 고지)를 언어별 HTML로 만들어 배포. 방법 후보: ① 빌드 뒤 헤드리스 브라우저로 각 주소를 열어 HTML 저장 (지금 구조 그대로) ② React Router 프레임워크 모드의 사전 렌더링으로 옮기기 ③ Next.js로 옮기기 (가장 큰 변경) — **① 추천** (발표 일정 안에 가능, 나머지 화면 코드는 그대로) | JavaScript 기반 사이트는 렌더링 방식이 검색에 영향 [S2] |
| `<html lang>` | 언어 URL에 맞게 (`en`, `zh-Hant`, `zh-Hans`, `vi`, `ja`, `ko`) | [S1] |
| **페이지별 제목·설명·canonical** | 예: `Daegu Dermatology Clinics — Hours & Booking Guide | MediDaegu`. 병원 상세는 `{병원 이름} — Hours, Location, Languages | MediDaegu`. 공통 컴포넌트로 `<head>`를 페이지마다 채우기 | 팀 판단 |
| **사이트맵** | `sitemap.xml`에 공개 페이지 × 언어 (병원 161곳 × 6개 언어 ≈ 966개 + 목록·가격·홈). 언어 버전을 사이트맵에서 묶는 방법도 있음 | 사이트맵으로 언어 버전 표시 가능 [S1][S3] |
| **robots.txt** | 로그인 화면(`/mypage`, `/booking`, `/chatbot`, `/reserve`, `/aftercare`, `/login`) 막기, 사이트맵 주소 적기 | [S4] |

### 2단계 — 무엇을 보여 줄까 (콘텐츠, 마케팅 + 프론트)

| 할 일 | 내용 |
|---|---|
| **병원 상세 페이지** | 공공데이터 그대로: 이름·주소·진료시간·진료과·외국어 상담 여부 + **출처·기준일**. 지도·"상담 요청" 버튼. 병원 소개 문구·후기·순위는 넣지 않음 (의료법) [S6] |
| **진료과 안내 페이지** (영어 먼저) | `/en/guide/dermatology` 등 4개: "How to book a dermatology clinic in Daegu" — 예약 절차·가격 범위 보는 법·진료시간 확인·회복 기간 묻기. SNS 콘텐츠 주제와 같음 ([마케팅-최신본.md](마케팅-최신본.md) 3장) |
| **노릴 검색어 (영어)** | `Daegu dermatology` · `Daegu clinic English` · `Korea skin clinic booking` · `Daegu eye clinic` · `Daegu health checkup` — **실제 검색량은 미확인** → Search Console을 연 뒤 실제 노출 검색어로 다시 고르기 |
| 쓰지 않을 검색어 | `best clinic in Daegu`, `cheapest` 등 순위·할인형 (의료법 · 팀 원칙) [S6] |
| **구조화 데이터 (JSON-LD)** | 병원 상세: `MedicalClinic`(이름·주소·전화·진료시간·좌표) · 모든 페이지: `BreadcrumbList` · 사이트: `Organization`(MediDaegu, 로고). **FAQ 구조화 데이터는 검색 결과 표시용으로는 기대하지 않음** — Google이 2023년부터 정부·보건 권위 사이트에만 보여 주다가, 이후 완전히 없앴다는 보도가 있음 [S7] (AI 답변용으로는 질문·답 형식 글 자체가 도움) |

### 3단계 — 등록하고 재기 (배포 뒤)

| 할 일 | 내용 |
|---|---|
| **Google Search Console** | 사이트 등록 → 사이트맵 제출 → 색인된 페이지 수·나라별·검색어별 노출·클릭 확인 (영어권·대만·일본·베트남 대부분이 Google) |
| Bing Webmaster Tools | 같은 사이트맵 제출 (AI 검색 일부가 Bing 색인을 쓴다는 이야기가 있으나 **미확인**) |
| 네이버 서치어드바이저 | 한국어 페이지용 — 낮은 우선순위 (타깃이 외국인) |
| 중국(바이두) | 중국 본토는 샤오훙수로 접근하기로 했고, 바이두 SEO는 **지금 하지 않음** (요건 미확인) |
| 속도 | 이미지 압축·지연 로딩, Lighthouse로 확인 |

## 3. 볼 숫자

| 숫자 | 어디서 | 처음 목표 |
|---|---|---|
| 색인된 페이지 수 | Search Console | 사이트맵 페이지의 대부분 (몇 주 걸림) |
| 노출 수 · 클릭 수 (나라·언어별) | Search Console | 측정 시작 |
| 진료과 안내 4개 페이지의 검색 노출 | Search Console | 측정 시작 |
| 검색으로 들어와 "상담 요청"까지 간 수 | 웹 분석 (이벤트) | 측정 시작 |

목표 숫자는 실제 데이터가 쌓인 뒤 정해요.

## 4. 누가 · 언제

| 단계 | 담당 | 시점 |
|---|---|---|
| 1단계 (언어 URL · 미리 그리기 · 제목 · 사이트맵) | **프론트** (일본어 화면 PR #52와 겹치지 않게 순서 조율) | 발표 전에는 계획·시연, 실제 반영은 배포 일정에 맞춰 |
| 2단계 (진료과 안내 4개 · 병원 상세 문구) | 마케팅(팀원 3) 글 + 프론트 페이지 | 1단계 뒤 |
| 3단계 (Search Console 등록) | 배포 담당 | 실제 주소(도메인) 정해진 뒤 — **도메인 미정** |

- 백엔드는 1단계에 필요 없음 (병원 데이터가 정적 JSON). 나중에 병원 데이터를 API로 바꾸면 빌드 때 API에서 받아 미리 그리면 됨

## 출처

| 번호 | 자료 | URL | 등급 | 기준 시점 | 확인일 |
|---|---|---|---|---|---|
| S1 | Google Search Central, Tell Google about localized versions of your page (언어별 URL·hreflang·사이트맵 방법) | https://developers.google.com/search/docs/specialty/international/localized-versions | 공식 | 현행 문서 | 2026-11-20 (검색 요약으로 확인) |
| S2 | Google Search Central, JavaScript SEO basics | https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics | 공식 | 현행 문서 | 2026-11-20 (주소만 확인, 본문 미확인) |
| S3 | Google Search Central, Sitemaps overview | https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview | 공식 | 현행 문서 | 2026-11-20 (주소만 확인, 본문 미확인) |
| S4 | Google Search Central, Introduction to robots.txt | https://developers.google.com/search/docs/crawling-indexing/robots/intro | 공식 | 현행 문서 | 2026-11-20 (주소만 확인, 본문 미확인) |
| S5 | 메디대구 환자용 웹 코드 (`index.html`, `src/main.tsx`, `src/i18n/index.ts`, `public/`) | frontend 브랜치 `apps/web-platform/` | 팀 내부 | 2026-11-20 | 2026-11-20 |
| S6 | 의료법 제56조 정리 | [../research/의료관광/규제-가격노출-의료광고.md](../research/의료관광/규제-가격노출-의료광고.md) | 공식 (팀 노트 경유) | 시행 2026-10-02 | 2026-11-20 |
| S7 | Google Search Central 블로그, Changes to HowTo and FAQ rich results (2023-08, 정부·보건 권위 사이트만) · 이후 FAQ 리치 결과 종료 보도 (Search Engine Journal) | https://developers.google.com/search/blog/2023/08/howto-faq-changes · https://www.searchenginejournal.com/google-drops-faq-rich-results/574429/ | 공식 + 언론 (종료는 Google 원문 미확인) | 2023-08 / 2026 | 2026-11-20 |
