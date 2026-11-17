# multi_agent 정리 선택지 (2026-11-17)

> 대상: `claude/keen-cray-j57504` 브랜치 (dd440a2 설계 문서, b26b397 1단계). 결정은 AI 담당(사용자)이 함
> 지금 상태: 새 폴더 `multi_agent/`에서 `google-genai` SDK로 Gemini를 **직접** 호출. `pyproject.toml`에 `google-genai`·`python-dotenv` 추가

## 왜 정리가 필요한가

| 기존 규칙·코드 | multi_agent와의 차이 |
|---|---|
| `backend/AGENTS.md` 6절: "LLM 호출은 `ai/llm/client.py`만 사용 (마스킹 거침)" | `ai/llm/client.py`를 거치지 않음 |
| `ai/llm/client.py`: OpenAI 호환 형식(httpx), Gemini → NVIDIA 순서로 넘어감, 재시도, 사용량 기록 | Gemini 하나만, 재시도·사용량 기록 없음 |
| `ai/llm/safety.py`: 응급 차단, 개인정보 마스킹, 의료 판단 가드 (LLM 부르기 전) | 안전 검사 없음 |
| `ai/agent/core/orchestrator.py`: 이미 "오케스트레이터 + 도구 9개 + 카드" 구조, 챗봇 API(`/chatbot/ask`)가 사용 중 | 같은 일을 하는 두 번째 오케스트레이터가 생김 |
| `.env`는 루트 하나 (`core/config.py`, `ai/llm/config.py`가 읽음) | 설계 문서는 `multi_agent/.env`, `python-dotenv` 추가 |

## 선택지

### A. 기존 `ai/` 안으로 옮기기 — `ai/llm/client.py` 사용 (추천)

`ai/agent/multi/`(또는 `ai/agent/core/sub_agents.py`)에 서브 에이전트를 만들고, 서브 에이전트 1개 = 기존 `ToolRegistry`에 등록하는 도구 1개로 감쌈. 모델 호출은 `LLMClient.chat()`

| 장점 | 단점 |
|---|---|
| 마스킹·응급 차단·의료 가드·재시도·제공자 전환·사용량 기록을 그대로 씀 → 규칙 위반 없음 | `google-genai` SDK 예제를 그대로 못 씀. OpenAI 형식(`tools`, `tool_calls`)으로 바꿔 써야 함 |
| 챗봇 API(`/chatbot/ask`)·카드·대화 저장에 바로 연결 가능 → 시연에 쓸 수 있음 | 기존 오케스트레이터 구조를 먼저 읽어야 해서 시작이 느림 |
| 새 의존성 없음, `.env` 하나 유지 | Gemini 전용 기능(SDK 자동 함수 호출 등)은 못 씀 (지금 계획은 수동 루프라 영향 작음) |
| 테스트(`ai/tests`)·평가(`ai/agent/eval`)를 같이 씀 | |

### B. `multi_agent/` 폴더 유지 + 안전 장치만 연결

`google-genai`로 계속 만들되, 호출 전에 `ai.llm.safety.check()`를 부르고 사용량을 기록하는 얇은 감싸기 함수를 둠

| 장점 | 단점 |
|---|---|
| 설계 문서·SDK 예제 그대로 진행, 학습이 빠름 | LLM 호출 경로가 두 개 → 재시도·제공자 전환·사용량 기록을 다시 만들어야 함 |
| Gemini 고유 기능을 바로 씀 | Gemini 한도(429)에 걸리면 NVIDIA로 넘어가지 못함 |
| | `AGENTS.md` 6절 규칙을 바꾸거나 예외로 적어야 함 (팀 알림 필요) |
| | 오케스트레이터가 두 개 → 챗봇 API에 붙이려면 결국 하나를 골라야 함 |
| | 공용 `pyproject.toml`·`uv.lock`에 의존성 2개 추가 |

### C. 실험용으로만 두고 합치지 않기

브랜치에서 구조를 익히는 데만 쓰고, 쓸 만한 부분은 나중에 A 방식으로 옮김

| 장점 | 단점 |
|---|---|
| 기존 코드·규칙에 영향 없음, 가장 빠르게 실험 | 옮길 때 다시 작성 → 작업 두 번 |
| 실패해도 버리면 됨 | 시연(12/9)에는 못 씀 |
| | 실험이라도 **가상 데이터만** 넣어야 함 (마스킹 없음) |
| | `pyproject.toml` 변경은 main에 합치지 않게 주의 |

## 비교

| 기준 | A | B | C |
|---|---|---|---|
| 규칙(마스킹·LLM 단일 경로) | 지킴 | 예외 필요 | 실험 한정 |
| 시연에 연결 | 바로 | 하나로 합쳐야 | 안 됨 |
| 시작 속도 | 느림 | 빠름 | 가장 빠름 |
| 장기 유지 비용 | 낮음 | 높음 (경로 2개) | 옮길 때 한 번 |

## 추천

**A**. 12/9 시연까지 챗봇 API에 붙일 생각이라면 A가 가장 적게 일함. SDK로 먼저 감을 잡고 싶다면 **C로 1~2단계만 실험 → A로 옮기기**

어느 쪽이든 먼저 정할 것: 서브 에이전트 목록과 역할 (설계 문서 5절), 지금 단일 오케스트레이터로 부족한 점이 무엇인지 (멀티 에이전트가 왜 필요한지)
