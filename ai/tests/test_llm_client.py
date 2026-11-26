"""ai/llm/client.py 테스트 — 실제 API 호출 없이 httpx.MockTransport로 확인."""

import json

import httpx
import pytest

from ai.llm.client import LLMClient, tool_result_message
from ai.llm.config import LLMSettings, ProviderConfig
from ai.llm.retry import AllProvidersFailed, RequestError

GEMINI = ProviderConfig("gemini", "https://gemini.test/v1", "k1", "gemini-model")
NEMOTRON = ProviderConfig("nemotron", "https://nim.test/v1", "k2", "nemo-model")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_hospitals",
            "description": "조건으로 병원 여러 곳 검색",
            "parameters": {"type": "object", "properties": {"department": {"type": "string"}}},
        },
    }
]


def ok_text(text="hello", model="m"):
    return httpx.Response(
        200,
        json={
            "model": model,
            "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 3},
        },
    )


def make_client(handler, providers=(GEMINI, NEMOTRON)):
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return LLMClient(list(providers), http=http, max_retries=2, sleep=lambda s: None)


def test_text_response_and_usage():
    client = make_client(lambda req: ok_text("안녕"))
    res = client.chat([{"role": "user", "content": "hi"}])
    assert res.text == "안녕" and res.provider == "gemini" and res.tool_calls == []
    assert client.tracker.totals()["gemini"]["prompt_tokens"] == 10


def test_request_body_has_tools_and_auth():
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        seen["auth"] = req.headers["authorization"]
        seen["body"] = json.loads(req.content)
        return ok_text()

    make_client(handler).chat([{"role": "user", "content": "x"}], tools=TOOLS)
    assert seen["url"] == "https://gemini.test/v1/chat/completions"
    assert seen["auth"] == "Bearer k1"
    assert seen["body"]["tools"] == TOOLS and seen["body"]["tool_choice"] == "auto"
    assert seen["body"]["model"] == "gemini-model"


def test_tool_call_parsing_and_missing_id():
    def handler(req):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {"type": "function", "function": {"name": "search_hospitals", "arguments": '{"department": "피부과"}'}},
                                {"id": "c2", "type": "function", "function": {"name": "search_hospitals", "arguments": "{broken"}},
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ]
            },
        )

    res = make_client(handler).chat([{"role": "user", "content": "흉터"}], tools=TOOLS)
    first, second = res.tool_calls
    assert first.name == "search_hospitals" and first.arguments == {"department": "피부과"}
    assert first.id.startswith("call_")  # id 없으면 생성
    assert second.arguments == {} and second.raw_arguments == "{broken"  # 깨진 JSON은 빈 dict + 원문 보관

    msg = res.as_assistant_message()
    assert msg["tool_calls"][0]["function"]["name"] == "search_hospitals"
    tr = tool_result_message(first.id, first.name, [{"name": "가상병원A"}])
    assert tr["role"] == "tool" and "가상병원A" in tr["content"]


def test_gemini_thought_signature_is_echoed_back():
    sig = {"google": {"thought_signature": "SIG123"}}

    def handler(req):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "extra_content": {"google": {"thought_signature": "MSGSIG"}},
                            "tool_calls": [
                                {
                                    "id": "c1",
                                    "type": "function",
                                    "function": {"name": "search_hospitals", "arguments": '{"department":"피부과"}'},
                                    "extra_content": sig,
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ]
            },
        )

    msg = make_client(handler).chat([{"role": "user", "content": "x"}], tools=TOOLS).as_assistant_message()
    assert msg["tool_calls"][0]["extra_content"] == sig
    assert msg["tool_calls"][0]["function"]["arguments"] == '{"department":"피부과"}'  # 원문 그대로
    assert msg["extra_content"]["google"]["thought_signature"] == "MSGSIG"


def test_429_falls_back_to_next_provider_without_retry():
    calls = []

    def handler(req):
        calls.append(req.url.host)
        if req.url.host == "gemini.test":
            return httpx.Response(429, json={"error": "RESOURCE_EXHAUSTED"})
        return ok_text("from nemotron")

    client = make_client(handler)
    res = client.chat([{"role": "user", "content": "x"}])
    assert res.provider == "nemotron" and res.text == "from nemotron"
    assert calls == ["gemini.test", "nim.test"]  # 429는 재시도 없이 바로 넘어감
    recs = client.tracker.records
    assert [r.ok for r in recs] == [False, True] and recs[1].fallback_from == "gemini"


def test_5xx_retries_then_succeeds_on_same_provider():
    count = {"n": 0}

    def handler(req):
        count["n"] += 1
        return httpx.Response(503) if count["n"] < 3 else ok_text()

    res = make_client(handler).chat([{"role": "user", "content": "x"}])
    assert res.provider == "gemini" and count["n"] == 3


def test_timeout_retries_then_falls_back():
    def handler(req):
        if req.url.host == "gemini.test":
            raise httpx.ReadTimeout("slow", request=req)
        return ok_text()

    assert make_client(handler).chat([{"role": "user", "content": "x"}]).provider == "nemotron"


def test_400_raises_without_fallback():
    calls = []

    def handler(req):
        calls.append(req.url.host)
        return httpx.Response(400, json={"error": "bad tool schema"})

    with pytest.raises(RequestError):
        make_client(handler).chat([{"role": "user", "content": "x"}])
    assert calls == ["gemini.test"]


def test_all_providers_fail():
    with pytest.raises(AllProvidersFailed):
        make_client(lambda req: httpx.Response(429)).chat([{"role": "user", "content": "x"}])


def test_no_keys_means_no_providers():
    s = LLMSettings(_env_file=None, gemini_api_key="", nemotron_api_key="k")
    assert {p.name for p in s.providers()} == {"nemotron"}  # 기본값이 모델 2개라 nemotron이 2번 나옴
    with pytest.raises(AllProvidersFailed):
        LLMClient([]).chat([{"role": "user", "content": "x"}])


def test_unknown_provider_name():
    with pytest.raises(ValueError):
        LLMSettings(_env_file=None, llm_provider_order="gemini,gpt").providers()


def test_comma_separated_models_become_fallback_chain():
    s = LLMSettings(_env_file=None, gemini_api_key="k", gemini_model="a, b", nemotron_api_key="k2", nemotron_model="n")
    assert [(p.name, p.model) for p in s.providers()] == [("gemini", "a"), ("gemini", "b"), ("nemotron", "nvidia/n")]


def test_nvidia_model_names_get_vendor_prefix():
    s = LLMSettings(_env_file=None, gemini_api_key="", nemotron_api_key="k",
                    nemotron_model="nemotron-3.5-lightning-30b-a3b, nvidia/nemotron-3.5-super-vl-120b-a12b")
    assert [p.model for p in s.providers()] == ["nvidia/nemotron-3.5-lightning-30b-a3b", "nvidia/nemotron-3.5-super-vl-120b-a12b"]
    other = LLMSettings(_env_file=None, gemini_api_key="", nemotron_api_key="k", nemotron_base_url="https://other.test/v1",
                        nemotron_model="nemotron-x")
    assert [p.model for p in other.providers()] == ["nemotron-x"]  # NVIDIA 주소가 아니면 건드리지 않음


# --- nemotron 숨은 생각(reasoning) 끄기 (2026-11-25, 응답 속도) ---------------------------


def test_nemotron_thinking_switch_is_sent_in_body():
    on = LLMSettings(_env_file=None, gemini_api_key="", nemotron_api_key="k2", nemotron_model="n")
    assert on.providers()[0].extra_body == {}  # 기본은 켬 (정확도 유지)
    s = LLMSettings(_env_file=None, gemini_api_key="k", gemini_model="g", nemotron_api_key="k2", nemotron_model="n",
                    nemotron_thinking=False)
    gem, nemo = s.providers()
    assert gem.extra_body == {}
    assert nemo.extra_body == {"chat_template_kwargs": {"enable_thinking": False}}

    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return ok_text()

    make_client(handler, providers=(nemo,)).chat([{"role": "user", "content": "x"}], tools=TOOLS)
    assert seen["body"]["chat_template_kwargs"] == {"enable_thinking": False} and seen["body"]["tools"] == TOOLS


def test_reasoning_content_is_not_echoed_back():
    def handler(req):
        return httpx.Response(200, json={"model": "m", "choices": [{"finish_reason": "tool_calls", "message": {
            "role": "assistant", "content": "", "reasoning_content": "긴 생각...",
            "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "search_hospitals", "arguments": "{}"}}]}}]})

    res = make_client(handler).chat([{"role": "user", "content": "x"}], tools=TOOLS)
    assert "reasoning_content" not in res.as_assistant_message()


# --- 모델·소요 시간 로그 (응답이 느린 이유를 배포 로그에서 보려고) ---------------------------


def test_success_logs_model_and_duration(caplog):
    caplog.set_level("INFO", logger="ai.llm")
    make_client(lambda req: ok_text("안녕", model="gemini-3.5-flash")).chat(
        [{"role": "user", "content": "hi"}], service="chatbot"
    )
    lines = [r.getMessage() for r in caplog.records if r.name == "ai.llm"]
    assert len(lines) == 1
    line = lines[0]
    assert line.startswith("llm ok ")
    assert "service=chatbot" in line and "provider=gemini" in line and "model=gemini-3.5-flash" in line
    assert "ms=" in line and "tokens=10/3" in line and "fallback_from=-" in line


def test_fallback_logs_failure_then_success(caplog):
    caplog.set_level("INFO", logger="ai.llm")

    def handler(req):
        if "gemini" in str(req.url):
            return httpx.Response(429, json={"error": "rate"})
        return ok_text(model="nemo-model")

    make_client(handler).chat([{"role": "user", "content": "hi"}])
    lines = [r.getMessage() for r in caplog.records if r.name == "ai.llm"]
    assert lines[0].startswith("llm fail ") and "provider=gemini" in lines[0] and "error=RateLimitError" in lines[0]
    assert lines[1].startswith("llm ok ") and "provider=nemotron" in lines[1] and "fallback_from=gemini" in lines[1]


def test_log_has_no_message_content_or_key(caplog):
    caplog.set_level("INFO", logger="ai.llm")
    make_client(lambda req: ok_text("비밀 답변")).chat([{"role": "user", "content": "개인 증상 내용"}])
    text = " ".join(r.getMessage() for r in caplog.records if r.name == "ai.llm")
    assert "개인 증상" not in text and "비밀 답변" not in text and "k1" not in text.split()


# --- 429 받은 모델은 잠시 뒤로 (2026-11-26, 막힌 모델을 매번 먼저 시도해 한 턴 75.8초) ---------------------------


def _counting_handler(statuses):
    """모델 이름별로 정해 둔 상태 코드를 돌려주고, 어느 모델을 몇 번째로 불렀는지 기록."""
    calls = []

    def handler(req):
        model = json.loads(req.content)["model"]
        calls.append(model)
        code = statuses.get(model, 200)
        return httpx.Response(429, text="quota") if code == 429 else ok_text(model=model)

    return handler, calls


def test_rate_limited_model_goes_to_the_back_until_cooldown_ends():
    now = [0.0]
    flash = ProviderConfig("gemini", "https://gemini.test/v1", "k1", "flash")
    lite = ProviderConfig("gemini", "https://gemini.test/v1", "k1", "lite")
    handler, calls = _counting_handler({"flash": 429})
    client = LLMClient([flash, lite], http=httpx.Client(transport=httpx.MockTransport(handler)), max_retries=0,
                       sleep=lambda s: None, rate_limit_cooldown=600, clock=lambda: now[0])

    assert client.chat([{"role": "user", "content": "1"}]).model == "lite"
    assert calls == ["flash", "lite"]  # 처음에는 순서대로
    calls.clear()
    assert client.chat([{"role": "user", "content": "2"}]).model == "lite"
    assert calls == ["lite"]  # 막힌 flash는 건너뜀 (lite가 성공해서 flash까지 안 감)

    now[0] = 601  # 쉬는 시간이 끝나면 다시 원래 순서
    calls.clear()
    client.chat([{"role": "user", "content": "3"}])
    assert calls[0] == "flash"


def test_when_every_model_is_cooling_they_are_still_tried():
    now = [0.0]
    a = ProviderConfig("gemini", "https://gemini.test/v1", "k1", "a")
    b = ProviderConfig("nemotron", "https://nim.test/v1", "k2", "b")
    statuses = {"a": 429, "b": 429}
    handler, calls = _counting_handler(statuses)
    client = LLMClient([a, b], http=httpx.Client(transport=httpx.MockTransport(handler)), max_retries=0,
                       sleep=lambda s: None, rate_limit_cooldown=600, clock=lambda: now[0])
    with pytest.raises(AllProvidersFailed):
        client.chat([{"role": "user", "content": "1"}])
    statuses["b"] = 200  # 한도가 풀림
    calls.clear()
    assert client.chat([{"role": "user", "content": "2"}]).model == "b"  # 둘 다 쉬는 중이어도 시도는 함
    assert calls == ["a", "b"]
    calls.clear()
    client.chat([{"role": "user", "content": "3"}])
    assert calls == ["b"]  # 성공한 b는 쉬는 목록에서 빠짐, a만 뒤로


def test_cooldown_comes_from_settings():
    s = LLMSettings(_env_file=None, gemini_api_key="k", llm_rate_limit_cooldown_seconds=30)
    assert LLMClient.from_settings(s).rate_limit_cooldown == 30
