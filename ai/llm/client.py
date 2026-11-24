"""LLM API 호출은 모두 이 모듈을 거친다 (챗봇·에이전트 공통).

- 제공자는 모두 OpenAI 호환 `/chat/completions` 형식 (Gemini, NVIDIA NIM 둘 다 지원)
  → 메시지·도구(tools) 형식이 하나로 통일되고, 새 SDK 의존성 없이 httpx만 사용
- 순서대로 시도: 429면 바로 다음 제공자, 5xx·타임아웃은 재시도 후 다음 제공자, 그 밖의 4xx는 즉시 실패
- 결과는 LLMResponse 하나로 정규화 (tool_calls의 arguments는 dict로 파싱)

사용 예:
    client = LLMClient.from_settings()
    res = client.chat(messages=[{"role": "user", "content": "hi"}], tools=[...], service="chatbot")
    if res.tool_calls: ...
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

from ai.llm.config import LLMSettings, ProviderConfig, get_settings
from ai.llm.retry import (
    AllProvidersFailed,
    LLMError,
    RateLimitError,
    RequestError,
    TransientError,
    classify_http_error,
    with_retry,
)
from ai.llm.usage_tracker import UsageRecord, UsageTracker

Message = dict[str, Any]  # OpenAI 형식: {"role": ..., "content": ..., "tool_calls"?: ..., "tool_call_id"?: ...}

# 호출마다 한 줄: 어느 모델이 답했고 몇 ms 걸렸는지 (배포 로그에서 느린 원인 찾기용).
# 대화 내용·키는 남기지 않음. 서버(uvicorn·Vercel)는 앱 로거를 따로 설정하지 않아 INFO가 버려지므로 여기서 직접 출력
log = logging.getLogger("ai.llm")
if not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(_h)
    log.setLevel(logging.INFO)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    raw_arguments: str = ""  # 파싱 실패 시 원문 확인용
    # 제공자 고유 필드 (예: Gemini 3의 extra_content.google.thought_signature).
    # 다음 요청에 그대로 돌려주지 않으면 Gemini 3는 도구 호출 대화를 거부할 수 있음
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    text: str | None
    tool_calls: list[ToolCall]
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str | None = None
    message_extra: dict[str, Any] = field(default_factory=dict, repr=False)  # 메시지 단위 제공자 고유 필드
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def as_assistant_message(self) -> Message:
        """대화 기록에 그대로 이어 붙일 assistant 메시지 (도구 호출 루프용)."""
        msg: Message = {"role": "assistant", "content": self.text or "", **self.message_extra}
        if self.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": tc.raw_arguments or json.dumps(tc.arguments, ensure_ascii=False)},
                    **tc.extra,
                }
                for tc in self.tool_calls
            ]
        return msg


def tool_result_message(tool_call_id: str, name: str, result: Any) -> Message:
    """도구 실행 결과를 모델에 돌려줄 메시지."""
    content = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
    return {"role": "tool", "tool_call_id": tool_call_id, "name": name, "content": content}


_STANDARD_TOOL_CALL_KEYS = {"id", "type", "function", "index"}
_STANDARD_MESSAGE_KEYS = {"role", "content", "tool_calls", "refusal", "annotations", "audio", "function_call"}


def _parse_response(provider: ProviderConfig, data: dict[str, Any]) -> LLMResponse:
    try:
        choice = data["choices"][0]
        message = choice.get("message") or {}
    except (KeyError, IndexError, TypeError) as e:
        raise TransientError(f"응답 형식 이상: {str(data)[:200]}", provider.name) from e

    calls: list[ToolCall] = []
    for tc in message.get("tool_calls") or []:
        fn = tc.get("function") or {}
        raw_args = fn.get("arguments") or "{}"
        if isinstance(raw_args, dict):  # 일부 제공자는 dict로 줌
            args, raw_str = raw_args, json.dumps(raw_args, ensure_ascii=False)
        else:
            raw_str = raw_args
            try:
                args = json.loads(raw_args) if raw_args.strip() else {}
            except json.JSONDecodeError:
                args = {}
        calls.append(
            ToolCall(
                id=tc.get("id") or f"call_{uuid.uuid4().hex[:12]}",  # id가 없는 제공자 대비
                name=fn.get("name", ""),
                arguments=args if isinstance(args, dict) else {},
                raw_arguments=raw_str,
                extra={k: v for k, v in tc.items() if k not in _STANDARD_TOOL_CALL_KEYS},
            )
        )

    usage = data.get("usage") or {}
    return LLMResponse(
        text=message.get("content"),
        tool_calls=calls,
        provider=provider.name,
        model=data.get("model") or provider.model,
        prompt_tokens=int(usage.get("prompt_tokens") or 0),
        completion_tokens=int(usage.get("completion_tokens") or 0),
        finish_reason=choice.get("finish_reason"),
        message_extra={k: v for k, v in message.items() if k not in _STANDARD_MESSAGE_KEYS},
        raw=data,
    )


class LLMClient:
    def __init__(
        self,
        providers: list[ProviderConfig],
        *,
        temperature: float = 0.2,
        timeout: float = 30.0,
        max_retries: int = 2,
        tracker: UsageTracker | None = None,
        http: httpx.Client | None = None,
        sleep=None,
    ):
        self.providers = providers
        self.temperature = temperature
        self.max_retries = max_retries
        self.tracker = tracker or UsageTracker()
        self._http = http or httpx.Client(timeout=timeout)
        self._sleep = sleep  # 테스트에서 대기 없애기용

    @classmethod
    def from_settings(cls, settings: LLMSettings | None = None, **kwargs) -> "LLMClient":
        s = settings or get_settings()
        return cls(
            s.providers(),
            temperature=s.llm_temperature,
            timeout=s.llm_timeout_seconds,
            max_retries=s.llm_max_retries,
            tracker=kwargs.pop("tracker", None) or UsageTracker(s.llm_usage_log_path),
            **kwargs,
        )

    # ------------------------------------------------------------------
    def chat(
        self,
        messages: list[Message],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        service: str = "chatbot",
        tenant_id: str | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        if not self.providers:
            raise AllProvidersFailed([])

        errors: list[LLMError] = []
        prev_failed: str | None = None
        for provider in self.providers:
            t0 = time.perf_counter()
            try:
                res = with_retry(
                    lambda p=provider: self._call(p, messages, tools, tool_choice, temperature),
                    max_retries=self.max_retries,
                    **({"sleep": self._sleep} if self._sleep else {}),
                )
            except RequestError as e:
                self._record(service, tenant_id, provider, ok=False, fallback_from=prev_failed)
                self._log(service, provider, t0, fallback_from=prev_failed, error=e)
                raise e  # 요청 자체 오류는 다른 제공자도 같을 가능성이 커서 넘기지 않음
            except (RateLimitError, TransientError) as e:
                self._record(service, tenant_id, provider, ok=False, fallback_from=prev_failed)
                self._log(service, provider, t0, fallback_from=prev_failed, error=e)
                errors.append(e)
                prev_failed = provider.name
                continue
            self._record(service, tenant_id, provider, ok=True, fallback_from=prev_failed, res=res)
            self._log(service, provider, t0, fallback_from=prev_failed, res=res, tools=len(tools or []))
            return res
        raise AllProvidersFailed(errors)

    # ------------------------------------------------------------------
    def _call(
        self,
        provider: ProviderConfig,
        messages: list[Message],
        tools: list[dict[str, Any]] | None,
        tool_choice: str | dict[str, Any] | None,
        temperature: float | None,
    ) -> LLMResponse:
        body: dict[str, Any] = {
            "model": provider.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = tool_choice or "auto"

        try:
            resp = self._http.post(
                f"{provider.base_url.rstrip('/')}/chat/completions",
                json=body,
                headers={"Authorization": f"Bearer {provider.api_key}"},
            )
        except (httpx.TimeoutException, httpx.TransportError) as e:
            raise TransientError(f"연결 실패: {e!r}", provider.name) from e

        if resp.status_code >= 400:
            raise classify_http_error(provider.name, resp)
        try:
            data = resp.json()
        except ValueError as e:
            raise TransientError("JSON 아닌 응답", provider.name) from e
        return _parse_response(provider, data)

    @staticmethod
    def _log(service, provider: ProviderConfig, t0: float, *, fallback_from, res=None, error=None, tools: int = 0):
        """예: `llm ok service=chatbot provider=gemini model=gemini-3.5-flash ms=8123 tokens=1200/80 tools=5 fallback_from=-`
        ms는 그 제공자에서 쓴 시간 (재시도 포함)."""
        ms = round((time.perf_counter() - t0) * 1000)
        base = f"service={service} provider={provider.name}"
        if res is not None:
            log.info(
                "llm ok %s model=%s ms=%d tokens=%d/%d tools=%d finish=%s fallback_from=%s",
                base, res.model, ms, res.prompt_tokens, res.completion_tokens, tools, res.finish_reason, fallback_from or "-",
            )
        else:
            log.warning(
                "llm fail %s model=%s ms=%d error=%s fallback_from=%s",
                base, provider.model, ms, type(error).__name__, fallback_from or "-",
            )

    def _record(self, service, tenant_id, provider: ProviderConfig, *, ok: bool, fallback_from, res=None):
        self.tracker.record(
            UsageRecord(
                service=service,
                provider=provider.name,
                model=res.model if res else provider.model,
                prompt_tokens=res.prompt_tokens if res else 0,
                completion_tokens=res.completion_tokens if res else 0,
                ok=ok,
                tenant_id=tenant_id,
                fallback_from=fallback_from,
            )
        )
