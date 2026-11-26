"""모델명·온도·타임아웃 설정. 값은 .env에서 읽는다.

제공자 순서: LLM_PROVIDER_ORDER (기본 "gemini,nemotron")
- gemini   : Google AI Studio 무료 키, OpenAI 호환 엔드포인트
- nemotron : NVIDIA build(NIM) 체험 API, OpenAI 호환 엔드포인트
- 둘 다 무료 등급은 입력이 기록·학습에 쓰일 수 있음 → 가상 데이터만 사용 (subject/plan.md 12-5)
- 유료 API로 바꿀 때는 제공자 하나를 추가하고 순서만 바꾸면 됨
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 어느 폴더에서 서버를 켜도 루트 .env를 읽도록 파일 위치 기준 (ai/llm/config.py → 저장소 루트). 백엔드 core/config.py와 같은 방식
ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key: str
    model: str
    # 요청 본문에 덧붙일 제공자 고유 값 (예: nemotron의 chat_template_kwargs)
    extra_body: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_ENV, env_file_encoding="utf-8", extra="ignore", env_ignore_empty=True
    )  # 빈 값(GEMINI_MODEL= 등)은 기본값 사용

    llm_provider_order: str = "gemini,nemotron"

    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    # 쉼표로 여러 모델을 적으면 앞 모델이 한도 초과(429)일 때 다음 모델로 넘어간다 (하루 한도가 모델별로 따로 있음)
    # 2026-11-09~10 무료 키로 확인: gemini-3.5-flash 응답 약 2초, **하루 20회** 한도(429 응답의 quotaValue).
    # 3.5-flash-lite는 응답함(하루 한도 수치 미확인). 3.8-flash·3.7-flash·flash-latest는 응답 없음(90초 초과),
    # 2.5-flash는 신규 사용자 불가(404)
    gemini_model: str = "gemini-3.5-flash,gemini-3.5-flash-lite"

    nemotron_api_key: str = ""
    nemotron_base_url: str = "https://integrate.api.nvidia.com/v1"
    # 2026-11-10 실제 키로 확인: 3.5-super-vl은 응답 0.4~2.6초, 도구 호출 됨. 3.5-lightning은 더 느리고 도구 선택이 덜 정확.
    # 3-nano-30b-a3b는 2026-09-01 종료(410), 3-super-120b-a12b는 이 계정에서 404
    nemotron_model: str = "nvidia/nemotron-3.5-super-vl-120b-a12b,nvidia/nemotron-3.5-lightning-30b-a3b"
    # nemotron-3.5는 기본으로 답 전에 숨은 생각 글(reasoning_content)을 길게 쓴다 → 출력 토큰·시간 대부분 (2026-11-25 측정:
    # "통역 돼요?" 기본 2.9초·304토큰 중 285가 생각 / 끄면 0.9초·16토큰). NEMOTRON_THINKING=false로 끌 수 있다.
    # 기본은 켬: 끄면 턴당 약 3배 빠르지만 시나리오 평가에서 체류 형태 기록·예약 상태 조회를 놓쳤다
    # (ai/agent/eval/results/2026-11-25-scenario-nemotron-thinking-*.md — 켬 12/12 두 번, 끔 10/12·4/6·11/12)
    nemotron_thinking: bool = True

    llm_temperature: float = 0.2
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2  # 같은 제공자에서 5xx·타임아웃 재시도 횟수
    # 한도 초과(429)를 받은 모델은 이 시간(초) 동안 뒤로 미룬다. 무료 키는 하루 한도라 막히면 매번 다시 막힘 —
    # 2026-11-26 로컬: 막힌 gemini-3.5-flash를 매 호출 먼저 시도하다 한 번은 62초 기다린 뒤 429 (한 턴 75.8초)
    llm_rate_limit_cooldown_seconds: float = 600.0
    llm_usage_log_path: str = ""  # 비우면 메모리에만 기록

    def providers(self) -> list[ProviderConfig]:
        """키가 있는 제공자만 순서대로 돌려준다."""
        table = {
            "gemini": (self.gemini_base_url, self.gemini_api_key, self.gemini_model),
            "nemotron": (self.nemotron_base_url, self.nemotron_api_key, self.nemotron_model),
        }
        order = [n.strip() for n in self.llm_provider_order.split(",") if n.strip()]
        unknown = [n for n in order if n not in table]
        if unknown:
            raise ValueError(f"알 수 없는 LLM 제공자: {unknown} (가능: {list(table)})")
        out: list[ProviderConfig] = []
        for name in order:
            base_url, key, models = table[name]
            if not key:
                continue
            for m in (x.strip() for x in models.split(",")):
                if not m:
                    continue
                # NVIDIA build는 모델 이름 앞에 제작사 접두사가 필요하다 (nvidia/nemotron-...).
                # 접두사 없이 쓰면 404 "page not found"만 나와 원인을 찾기 어려움 (2026-11-10 확인)
                if name == "nemotron" and "nvidia.com" in base_url and "/" not in m:
                    m = f"nvidia/{m}"
                extra = {}
                if name == "nemotron" and not self.nemotron_thinking:
                    extra = {"chat_template_kwargs": {"enable_thinking": False}}
                out.append(ProviderConfig(name, base_url, key, m, extra))
        return out


@lru_cache
def get_settings() -> LLMSettings:
    return LLMSettings()
