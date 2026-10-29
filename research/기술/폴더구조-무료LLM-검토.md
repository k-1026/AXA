# 폴더 구조 제안 검토 + 무료 LLM(Nemotron 3) 가능 여부

> 작성 2026-10-29 · 대상: 팀에서 공유된 모노레포 구조안 · 규제 근거는 `research/의료관광/규제-*.md`

## 결론
- **구조안 방향은 좋음** — features↔modules 이름 맞춤, i18n 분리, `ai/eval`, `etl` 커밋 규칙이 특히 좋음
- **고칠 점 3가지**: 규제와 부딪히는 기능 폴더(discount·consultation·aftercare), 현재 `data/` 구조와의 차이, LLM 교체 가능하게 만들기
- **Nemotron 3 무료 API: 시제품·발표용으로는 가능, 서비스용은 어려움** — 공식 지원 언어에 한국어·베트남어·러시아어·몽골어가 없고, 무료 엔드포인트는 체험판이라 입력 내용이 기록됨

## 1. 구조안 검토

### 그대로 두면 좋은 것
| 항목 | 이유 |
|---|---|
| `frontend/features` ↔ `backend/modules` 같은 이름 | 담당자·기능 찾기 쉬움 |
| `i18n/locales/` | UI 번역은 파일로 고정 → 실행 중 API 비용 없음 |
| `ai/eval/` | 챗봇이 틀린 병원·가격 말하는지 테스트셋으로 확인 가능 |
| `data/etl/` 반드시 커밋 | 지금은 가공 스크립트가 저장소에 없음 → 다시 만들 수 있게 해야 함 |
| `.env.example` | 이미 있음 |

### 바꾸거나 추가할 것
| # | 제안 | 이유 |
|---|---|---|
| 1 | `features/discount`, `modules/discount` → **이름·범위 재검토** (예: `price-guide`에 통합, 공공 가격만) | 이벤트 할인가·할인율 노출은 의료광고 위험 → 서비스 경계에서 "하지 않는다"로 정함 ([규제-가격노출-의료광고.md](../의료관광/규제-가격노출-의료광고.md)) |
| 2 | `consultation`은 **확장 단계**로, MVP는 병원 공식 채널 링크 | 1:1 상담 조건(등록 유치의료기관만, 대가 X, 원문 번역만) ([규제-1대1상담.md](../의료관광/규제-1대1상담.md)) |
| 3 | `aftercare`도 확장 단계 + 법 검토 표시 | 사후 Q&A를 의사가 하면 비대면진료. 같은 병원 대면 기록이 있으면 요건(의료법 제34조의2 제2항 제1호)은 맞을 수 있으나, 우리가 **비대면진료 중개매체 신고 대상**(제34조의8)이 될 수 있음. 사진 = 건강 정보 |
| 4 | `data/`는 **지금 구조 유지**: `raw/ interim/ processed/` + `etl/ schemas/` 추가 | 이미 raw/interim/processed로 정리·커밋됨. 구조안에는 `interim`이 없음 → 수동 입력 시트 둘 곳이 없어짐 |
| 5 | `data/raw` 전체 gitignore 대신 **지금 규칙 유지** (실명 원본·크롤링만 제외) | 공공데이터 원본은 이미 `research-data`에 커밋됨. DVC는 6주 프로젝트에 과함 |
| 6 | `docs/compliance.md` 추가 | 서비스 경계 표(할 것/안 할 것)를 개발자가 바로 보게 |
| 7 | `research/`, `subject/`는 **루트에 그대로** (또는 `docs/` 아래로 한 번에 이동) | 노트 사이 상대 링크가 많음 → 옮기면 한 번에 |
| 8 | `ai/providers/` 추가 (LLM 호출을 한 곳으로) | 무료 API 정책이 자주 바뀜 → 모델 교체를 `.env` 한 줄로 |
| 9 | `CODEOWNERS`는 GitHub 아이디만 | 공개 저장소, 실명 금지 규칙 |
| 10 | 빈 폴더를 미리 다 만들지 말고 **MVP 기능부터** | 발표 11/9까지 11일. `map`·`hospital`·`price-guide`·`chatbot` 먼저 |

## 2. Nemotron 3 무료 API

### 무료로 쓰는 경로
| 경로 | 모델 | 조건 |
|---|---|---|
| NVIDIA build.nvidia.com (NIM API) | Nemotron 3 Nano 30B-A3B 등 | "NVIDIA API Trial Terms of Service" 적용 체험 서비스 [1]. 한도는 공식 문서에서 못 찾음 — NVIDIA 포럼 사용자 글에는 분당 40회 기준으로 429 오류를 겪는다는 내용 [2] (**공식 수치 미확인**) |
| OpenRouter `nvidia/nemotron-3-nano-30b-a3b:free` | Nano | 입출력 $0, 컨텍스트 256K, **"trial use only", 프롬프트·출력이 제공자 모델 개선용으로 기록됨** [3] |
| OpenRouter `nvidia/nemotron-3-embed-1b:free` | 임베딩(RAG용) | 무료, 사용 기록됨 [4] |
| 가중치 직접 실행 (Hugging Face·Ollama) | Nano | "NVIDIA Nemotron Open Model License", 상업 사용 가능 명시 [1] — 단 GPU 필요 |

### 우리 서비스에 걸리는 문제
1. **언어**: Nano 공식 지원 = 영어·독일어·스페인어·프랑스어·이탈리아어·일본어 [1]. Super(NIM·배포판)는 여기에 중국어 추가 [5]. **한국어·러시아어·베트남어·몽골어는 공식 지원 목록에 없음** (Super 기본(Base) 모델 카드는 한국어·러시아어 포함 20개 언어 표기 [6], 지시형 모델에서도 되는지는 미확인)
   → 우리 대상 국적(중국·대만·일본 등, [상위-데이터-확장-조사.md](../의료관광/상위-데이터-확장-조사.md))과 일부만 맞음
2. **개인정보**: 무료 엔드포인트는 입력이 기록됨 [3] → 환자 증상·사진·상담 내용을 넣으면 안 됨 (1:1 상담 번역에 무료 API 사용 불가에 가까움)
3. **안정성**: 체험판이라 한도·제공 여부가 바뀔 수 있음 → `ai/providers/`로 교체 가능하게

### 비용 줄이는 설계
| 기능 | 방법 | 실행 중 API 비용 |
|---|---|---|
| UI·병원 정보 번역 | `i18n/locales` 파일과 병원 정보 번역본을 **미리 한 번 생성** 후 사람이 검수, 커밋 | 없음 |
| 챗봇 | 지원 언어(영·일·중)는 Nemotron, 나머지는 **미리 만든 FAQ·필터 검색**으로 대체 | 질문당 1회 |
| RAG 임베딩 | 병원 데이터는 공개 정보 → 무료 임베딩 사용 가능, **한 번 만들어 저장** | 문서 변경 시만 |
| 1:1 상담 번역 | MVP 제외 (확장 단계에서 유료·비기록 API 또는 직접 실행) | — |

→ **"가능하다"의 범위**: 발표 데모·시제품(공개 정보만 다루는 챗봇·검색) = 가능 / 실제 환자 대화 번역 = 무료 API로는 불가에 가까움

## 3. 남은 확인
- build.nvidia.com 무료 한도 공식 수치 (계정 대시보드에서 확인)
- Nemotron 3 Super 지시형 모델의 한국어·러시아어 실제 품질 → `ai/eval`로 직접 테스트 (팀원 3 "저렴한 모델 언어별 테스트"와 연결)
- 다른 무료 경로(다른 회사 무료 티어) 비교는 **미조사**

## 출처
| # | 이름 | URL | 등급 | 확인일 |
|---|---|---|---|---|
| [1] | NVIDIA NIM API 문서 · Nemotron 3 Nano 30B-A3B 모델 개요 | https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-nano-30b-a3b | 공식 | 2026-10-29 |
| [1-1] | build.nvidia.com · Nemotron 3 Nano 모델 카드 | https://build.nvidia.com/nvidia/nemotron-3-nano-30b-a3b/modelcard | 공식 | 2026-10-29 (검색 결과) |
| [2] | NVIDIA 개발자 포럼 · NIM API 한도 상향 요청 글 | https://forums.developer.nvidia.com/t/request-for-nvidia-nim-api-rate-limit-increase-40-200-rpm/376516 | 사용자 글 | 2026-10-29 (검색 결과) |
| [3] | OpenRouter · nvidia/nemotron-3-nano-30b-a3b:free | https://openrouter.ai/nvidia/nemotron-3-nano-30b-a3b:free | 공식(제공사) | 2026-10-29 (검색 결과, 페이지 직접 접속 실패) |
| [4] | OpenRouter · nvidia/nemotron-3-embed-1b:free | https://openrouter.ai/nvidia/nemotron-3-embed-1b:free | 공식(제공사) | 2026-10-29 (검색 결과) |
| [5] | Azure AI Foundry · NVIDIA Nemotron 3 Super NIM | https://ai.azure.com/catalog/models/NVIDIA-Nemotron-3-Super-NIM-microservice | 공식(배포사) | 2026-10-29 (검색 결과) |
| [6] | Hugging Face · NVIDIA-Nemotron-3-Super-120B-A12B-Base-BF16 | https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-Base-BF16 | 공식 | 2026-10-29 (검색 결과) |
| [7] | 의료법 제34조의2, 제34조의8 | https://www.law.go.kr/법령/의료법 | 공식 | 2026-10-29 |
