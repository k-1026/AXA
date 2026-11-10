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
    assert [(p.name, p.model) for p in s.providers()] == [("gemini", "a"), ("gemini", "b"), ("nemotron", "n")]
