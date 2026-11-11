"""챗봇 API (7b): POST /chatbot/ask, DELETE /chatbot/sessions/{id}. 가짜 LLM, 메모리 SQLite, 가상 값만."""

import json
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.agent.service import DRAFT_KEPT_KEYS, RateLimiter
from ai.llm.client import LLMResponse, ToolCall
from ai.llm.retry import AllProvidersFailed
from modules.chatbot import service as chat_service
from modules.chatbot.models import ChatMessage, ChatSession
from modules.chatbot.store import DbSessionStore

from test_auth_patient import auth, signup, withdraw

ASK = "/api/v1/chatbot/ask"


class ScriptLLM:
    def __init__(self, script):
        self.script, self.calls = list(script), []

    def chat(self, messages, *, tools=None, service="chatbot", **kw):
        self.calls.append(messages)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def say(text):
    return LLMResponse(text=text, tool_calls=[], provider="fake", model="fake")


def call(name, args, cid="c1"):
    return LLMResponse(text=None, tool_calls=[ToolCall(id=cid, name=name, arguments=args)], provider="fake", model="fake")


@pytest.fixture
def llm(client):
    from main import app

    fake = ScriptLLM([])
    app.dependency_overrides[chat_service.get_llm] = lambda: fake
    app.dependency_overrides[chat_service.get_limiter] = lambda: RateLimiter(per_minute=1000, per_day=10000)
    yield fake
    app.dependency_overrides.clear()


def db(engine) -> Session:
    return Session(engine, expire_on_commit=False)


def ask(client, token, message, session_id=None, language=None):
    body = {"message": message, "session_id": session_id}
    if language:
        body["language"] = language
    return client.post(ASK, headers=auth(token), json=body)


# ------------------------------------------------------------------ 로그인·입력
def test_login_required(client, llm):
    r = client.post(ASK, json={"message": "hi"})
    assert r.status_code == 401 and r.json()["code"] == "auth.required"
    assert client.delete(f"/api/v1/chatbot/sessions/{uuid.uuid4()}").status_code == 401


def test_input_validation(client, llm):
    token = signup(client)
    assert ask(client, token, "").json()["code"] == "validation"
    assert ask(client, token, "x" * 1001).json()["code"] == "validation"
    r = ask(client, token, "hi", language="ja")
    assert r.status_code == 422 and r.json()["code"] == "validation" and r.json()["detail"]["language"] == "ja"
    assert llm.calls == []


# ------------------------------------------------------------------ 대화와 저장
def test_first_ask_creates_db_session_with_masked_text_only(client, llm, db_engine):
    token = signup(client)
    llm.script = [say("Hello!")]
    r = ask(client, token, "Hi, my email is kim.test@example.com")
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["text"] == "Hello!" and body["cards"] == [] and body["ai_generated"] is True and body["blocked"] is False
    with db(db_engine) as s:
        sess = s.get(ChatSession, uuid.UUID(body["session_id"]))
        assert sess.title == "Hi, my email is [email]"
        assert sess.lang == "zh-TW"  # 언어를 안 보내면 계정 선호 언어
        msgs = s.scalars(select(ChatMessage).order_by(ChatMessage.id)).all()
        assert [(m.role, m.content) for m in msgs] == [("user", "Hi, my email is [email]"), ("assistant", "Hello!")]


def test_follow_up_reads_history_from_db_and_restores_shown_hospitals(client, llm, db_engine):
    token = signup(client)
    llm.script = [
        call("search_hospitals", {"department": "피부과", "district": "수성구", "language": "en"}),
        say("Two clinics found."),
        say("OK, the first one."),
    ]
    sid = ask(client, token, "acne scar clinics in Suseong-gu", language="en").json()["session_id"]
    with db(db_engine) as s:
        shown = s.get(ChatSession, uuid.UUID(sid)).state["shown_hospitals"]
        assert shown and set(shown[0]) == {"id", "name"}
        assert "Two clinics" in s.scalars(select(ChatMessage.content)).all()[-1]  # 도구 결과는 저장 X, 텍스트만
    r = ask(client, token, "the first one please", session_id=sid, language="en")
    assert r.status_code == 200
    last = llm.calls[-1]
    assert [m["content"] for m in last if m["role"] in ("user", "assistant")][:2] == [
        "acne scar clinics in Suseong-gu", "Two clinics found."]
    assert f"id {shown[0]['id']}" in last[0]["content"]  # "방금 보여 준 병원"이 시스템 맥락으로 복원됨


def test_draft_saved_without_health_info_or_inquiry(client, llm, db_engine):
    token = signup(client)
    me = client.get("/api/v1/me", headers=auth(token)).json()
    with db(db_engine) as s:
        sid = DbSessionStore(s).create(me["id"], "en", "t", {"residency": "short_term"}).id
    secret = "scars on both cheeks since 2024"
    llm.script = [
        call("prepare_booking_request", {"hospital_id": 9002, "preferred_slots": ["2026-12-04 10:00"], "language": "en",
                                         "inquiry": "scar laser options", "nationality": "TW", "visa_needed": False,
                                         "health_info": secret}),
        say("Check the card."),
    ]
    r = ask(client, token, "book clinic B", session_id=sid, language="en")
    assert r.status_code == 200, r.json()
    card = next(c for c in r.json()["cards"] if c["type"] == "booking_draft")["data"]
    assert card["request"]["health_info"] == secret  # 제출용 값은 화면 카드로만 나감
    with db(db_engine) as s:
        state = s.get(ChatSession, uuid.UUID(sid)).state
    dumped = json.dumps(state, ensure_ascii=False)
    assert secret not in dumped and "scar laser" not in dumped
    assert set(state["draft"]) <= set(DRAFT_KEPT_KEYS)


# ------------------------------------------------------------------ 격리·삭제
def test_other_patient_cannot_continue_or_delete_my_session(client, llm, db_engine):
    mine = signup(client)
    other = signup(client, email="patient2@example.com")
    llm.script = [say("Hello!")]
    sid = ask(client, mine, "hi").json()["session_id"]

    r = ask(client, other, "show me", session_id=sid)
    assert r.status_code == 404 and r.json()["code"] == "not_found"
    r = client.delete(f"/api/v1/chatbot/sessions/{sid}", headers=auth(other))
    assert r.status_code == 404 and r.json()["code"] == "not_found"
    with db(db_engine) as s:
        assert s.get(ChatSession, uuid.UUID(sid)) is not None
    assert len(llm.calls) == 1  # 남의 세션 요청은 LLM까지 가지 않음


def test_delete_my_session_then_it_is_gone(client, llm, db_engine):
    token = signup(client)
    llm.script = [say("Hello!")]
    sid = ask(client, token, "hi").json()["session_id"]
    assert client.delete(f"/api/v1/chatbot/sessions/{sid}", headers=auth(token)).status_code == 204
    with db(db_engine) as s:
        assert s.get(ChatSession, uuid.UUID(sid)) is None
        assert s.scalars(select(ChatMessage)).all() == []
    assert ask(client, token, "again", session_id=sid).status_code == 404
    assert client.delete(f"/api/v1/chatbot/sessions/{sid}", headers=auth(token)).status_code == 404
    assert client.delete("/api/v1/chatbot/sessions/not-a-uuid", headers=auth(token)).status_code == 404


def test_withdraw_deletes_chat_sessions(client, llm, db_engine):
    token = signup(client)
    llm.script = [say("Hello!")]
    ask(client, token, "hi")
    assert withdraw(client, token).status_code == 204
    with db(db_engine) as s:
        assert s.scalars(select(ChatSession)).all() == [] and s.scalars(select(ChatMessage)).all() == []


# ------------------------------------------------------------------ 제한·장애
def test_rate_limited(client, llm):
    from main import app

    tight = RateLimiter(per_minute=1, per_day=10)
    app.dependency_overrides[chat_service.get_limiter] = lambda: tight
    token = signup(client)
    llm.script = [say("one"), say("two")]
    assert ask(client, token, "hi").status_code == 200
    r = ask(client, token, "hi again")
    assert r.status_code == 429 and r.json()["code"] == "rate_limited" and r.json()["detail"]["limit"] == "minute"


def test_all_llm_providers_failing_returns_503_without_saving(client, llm, db_engine):
    token = signup(client)
    llm.script = [AllProvidersFailed([])]
    r = ask(client, token, "hi")
    assert r.status_code == 503 and r.json()["code"] == "chatbot.unavailable"
    with db(db_engine) as s:
        assert s.scalars(select(ChatSession)).all() == []
