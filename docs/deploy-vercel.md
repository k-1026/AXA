# deploy-vercel.md — Vercel 배포 (2026-11-20 초안 → 2026-11-24 첫 배포)

> 상태: **2026-11-24 배포됨** (아래 0절). Cron `vercel.json`은 배포 확인 뒤 커밋 (`backend-A-vercel-cron`)
> 관련: 결정 12(Supabase + Vercel), [dashboard-integration.md](dashboard-integration.md), contracts 7-1(정기 정리)

## 0. 지금 배포 상태 (2026-11-24)

| 프로젝트 | 주소 | Root | 설정 |
|---|---|---|---|
| 백엔드 `axa` | https://axa-seven.vercel.app | 저장소 루트 (`index.py`) | FastAPI, 리전 **sin1**(Supabase 싱가포르), Ignored Build Step = **Only build production** |
| 환자 웹 `axa-tqse` | https://axa-tqse.vercel.app | `apps/web-platform` | Vite, Include files outside root **켜짐**, Ignored Build Step = **Only build production**, `apps/web-platform/vercel.json`(모든 주소 → index.html) |

- 두 프로젝트 모두 **main에 머지될 때만** 배포 (다른 브랜치 push는 건너뜀 → research-data 등 실패 메일 없음)
- 백엔드 `CORS_ORIGINS` = `["https://axa-tqse.vercel.app","http://localhost:5173"]`
- 백엔드 `LLM_PROVIDER_ORDER` = `nemotron,gemini` (11/24 연습용, 비용 X). 시연 전 Gemini로 되돌릴지 결정 — Nemotron은 약 2배 빠르지만 질문을 건너뛴 적 있음 (`docs/시나리오.md` 8-2, 로컬 문서)
- 환경변수를 바꾸면 **Redeploy** 필요. Redeploy 때 Vercel 계정 2단계 인증 코드를 물음 (사람이 입력)
- 공개 배포에서만 예약 화면에 "예시 일정 · 실제 예약 아님" (#92)
- 확인: `/api/v1/health` 200, 병원 목록 DB 조회, 시연 흐름(로그인 → 챗봇 → 9001 요청 → 대시보드 확정 → 사후관리 답장) 통과

## 1. 프로젝트 2개

| Vercel 프로젝트 | Root Directory | 내용 | 상태 |
|---|---|---|---|
| 환자 웹 | `apps/web-platform` | Vite 정적 빌드 (병원 대시보드도 이 안의 `/dashboard`). **"Include files outside the root directory" 켜기** (빌드 때 `data/`에서 병원 JSON을 만듦, 꺼지면 병원 0곳) | 설정 있음 |
| 백엔드 | 저장소 루트 | FastAPI (`backend/src/main.py`) + `ai/` 패키지 | 배포됨 (11/24) |

## 2. 환경변수

### 환자 웹
| 이름 | 값 |
|---|---|
| `VITE_API_URL` | 백엔드 주소 (예: `https://<백엔드>.vercel.app`) |

### 백엔드 (비밀 값은 Vercel에만, 저장소·채팅 X)
| 이름 | 필수 | 메모 |
|---|---|---|
| `JWT_SECRET` | O | 32자 이상 무작위 |
| `DATABASE_URL` | O | Supabase **pooler** 주소 (서버리스 → 연결 수 제한) |
| `CORS_ORIGINS` | O | `["https://<환자웹>"]` (JSON 목록, 대시보드도 같은 주소) |
| `CRON_SECRET` | O | 16자 이상. 없으면 정기 정리 API가 꺼짐(404) |
| `SUPABASE_URL` · `SUPABASE_SERVICE_ROLE_KEY` | 사진 쓸 때 | 비밀 키는 `sb_secret_…` (공개 키 `sb_publishable_` X). 없으면 "사진 있음"만 |
| `GEMINI_API_KEY` · `GEMINI_MODEL` (· `NEMOTRON_*`) | 챗봇·번역 | `LLM_PROVIDER_ORDER` 기본 `gemini,nemotron` |
| `ECOS_API_KEY` | 환율 | 없으면 저장된 환율만 |
| `JWT_PATIENT_EXPIRE_MINUTES` · `JWT_STAFF_EXPIRE_MINUTES` | X | 기본 1440 · 480 |
| `LLM_USAGE_LOG_PATH` | X | 서버리스는 파일이 남지 않으니 비움 |

## 3. Cron (정기 정리)

`GET /api/v1/internal/purge` 하루 1번 — 30일 지난 챗봇 대화, 끝난 로그인 세션, **DB에 없는 사진·영상 파일**(결정 23). Vercel Cron은 `CRON_SECRET`이 있으면 `Authorization: Bearer`를 자동으로 붙임

백엔드 프로젝트 루트 `vercel.json` (11/24 커밋):

```json
{
  "crons": [
    { "path": "/api/v1/exchange-rates", "schedule": "0 1 * * *" },
    { "path": "/api/v1/internal/purge", "schedule": "0 1 * * *" }
  ]
}
```

- 둘 다 `0 1 * * *` = 매일 UTC 01시 = **한국 10시** (11/24 사용자 결정). 무료 플랜은 하루 1번·시각은 그 1시간 안 어딘가(±59분 → 10:00~10:59)
- 환율: 10시가 환율 적용일이 바뀌는 시각(fx/service.py)이라 그때 한국은행 ECOS 값을 미리 받아 둠. Cron이 안 돌아도 요청 때 받아 오므로 안내는 그대로 정확
- 정리: 10시(서비스 시간 중)에 돌지만 30일 지난 대화·끝난 세션·안 쓰는 파일만 지움

## 4. 백엔드를 Vercel에 올리는 방법 (확인 필요)

- **진입 파일 = 루트 `index.py`** (2026-11-23 추가): Vercel FastAPI는 기본 위치(루트 `index.py` 등)에서 `app`을 찾음. 처음 배포 때 `FASTAPI_ENTRYPOINT_NOT_FOUND`(`backend/src/main.py`만 찾음)가 나서 추가 — `sys.path`에 `backend/src`·루트를 넣고 `from main import app`. Vercel이 제안한 `[tool.vercel] entrypoint = "backend.src.main:app"`은 `core`·`modules`·`ai` import 경로가 안 맞아 쓰지 않음
- **`.vercelignore`** (루트): 서버리스 함수 용량 제한(250MB) 대비 큰 자료(`data/raw`·`data/interim`(영업정보 빼고)·research·발표 등) 제외. 백엔드가 실행 중에 읽는 파일은 `data/processed/demo/demo_hospitals.json`뿐
- 의존성은 `pyproject.toml` / `uv.lock` (Vercel이 읽는지 확인, 안 되면 `requirements.txt` 생성)
- 지역: `icn1`(서울) 또는 `sin1` — Supabase 프로젝트 지역과 가깝게
- 이 PC의 psycopg 차단 문제(앱 제어)는 Vercel(Linux)에는 해당 없음 → `PSYCOPG_IMPL` 넣지 않음

## 5. 배포 전에 할 것

1. 브랜치 머지 (backend → main), Supabase 마이그레이션 `head`(지금 0009) 확인
2. 위 환경변수 입력 → 백엔드 배포 → `/api/v1/health` 200 확인
3. 환자 웹 `VITE_API_URL`·대시보드 주소 넣고 다시 배포
4. 공개 배포에서만 예시 예약 시간에 "예시 일정 · 실제 예약 아님" 문구 (메모리 결정)
5. 시연 계정으로 로그인 → 예약 → 대시보드 확정 → 사후관리 한 바퀴
