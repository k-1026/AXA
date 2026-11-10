"""모델명·온도·타임아웃 설정. 값은 .env에서 읽는다.

제공자 순서: LLM_PROVIDER_ORDER (기본 "gemini,nemotron")
- gemini   : Google AI Studio 무료 키, OpenAI 호환 엔드포인트
- nemotron : NVIDIA build(NIM) 체험 API, OpenAI 호환 엔드포인트
- 둘 다 무료 등급은 입력이 기록·학습에 쓰일 수 있음 → 가상 데이터만 사용 (subject/plan.md 12-5)
- 유료 API로 바꿀 때는 제공자 하나를 추가하고 순서만 바꾸면 됨
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key: str
    model: str


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_ignore_empty=True
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

    llm_temperature: float = 0.2
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2  # 같은 제공자에서 5xx·타임아웃 재시도 횟수
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
            out += [ProviderConfig(name, base_url, key, m.strip()) for m in models.split(",") if m.strip()]
        return out


@lru_cache
def get_settings() -> LLMSettings:
    return LLMSettings()
