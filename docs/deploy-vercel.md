# deploy-vercel.md — Vercel 배포 준비 (2026-11-20 초안)

> 상태: **배포해 본 적 없음**. 아래 백엔드 설정 파일은 제안이고, 실제 배포로 확인한 뒤 저장소에 넣는다 (확인 안 된 설정을 커밋하지 않음)
> 관련: 결정 12(Supabase + Vercel), [dashboard-integration.md](dashboard-integration.md), contracts 7-1(정기 정리)

## 1. 프로젝트 2개

| Vercel 프로젝트 | Root Directory | 내용 | 상태 |
|---|---|---|---|
| 환자 웹 | `apps/web-platform` | Vite 정적 빌드 (병원 대시보드도 이 안의 `/dashboard`). **"Include files outside the root directory" 켜기** (빌드 때 `data/`에서 병원 JSON을 만듦, 꺼지면 병원 0곳) | 설정 있음 |
| 백엔드 | 저장소 루트 | FastAPI (`backend/src/main.py`) + `ai/` 패키지 | **새로 만들어야 함** |

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

백엔드 프로젝트 루트 `vercel.json` (제안):

```json
{
  "crons": [{ "path": "/api/v1/internal/purge", "schedule": "0 18 * * *" }]
}
```

- `0 18 * * *` = 매일 UTC 18시 (한국 새벽 3시). 무료 플랜은 하루 1번·±59분
- 환율은 Cron 없이도 요청 때 받아 옴 (fx/service.py) → 따로 등록 안 해도 됨

## 4. 백엔드를 Vercel에 올리는 방법 (확인 필요)

- Vercel Python 런타임은 FastAPI `app`을 찾아 실행. 이 저장소는 `backend/src`와 루트의 `ai/`를 같이 불러와야 해서 **진입 파일**이 필요할 수 있음 (예: 루트 `api/index.py`에서 `sys.path`에 `backend/src`·루트를 넣고 `from main import app`)
- 의존성은 `pyproject.toml` / `uv.lock` (Vercel이 읽는지 확인, 안 되면 `requirements.txt` 생성)
- 지역: `icn1`(서울) 또는 `sin1` — Supabase 프로젝트 지역과 가깝게
- 이 PC의 psycopg 차단 문제(앱 제어)는 Vercel(Linux)에는 해당 없음 → `PSYCOPG_IMPL` 넣지 않음

## 5. 배포 전에 할 것

1. 브랜치 머지 (backend → main), Supabase 마이그레이션 `head`(지금 0009) 확인
2. 위 환경변수 입력 → 백엔드 배포 → `/api/v1/health` 200 확인
3. 환자 웹 `VITE_API_URL`·대시보드 주소 넣고 다시 배포
4. 공개 배포에서만 예시 예약 시간에 "예시 일정 · 실제 예약 아님" 문구 (메모리 결정)
5. 시연 계정으로 로그인 → 예약 → 대시보드 확정 → 사후관리 한 바퀴
