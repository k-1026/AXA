"""ai/agent/service.py — 7a 서비스 층 (가짜 LLM, 메모리 저장소, 가짜 예약 저장소)."""

from datetime import datetime, timedelta, timezone

import pytest

from ai.agent import service as svc
from ai.agent.service import ChatService, ChatServiceError, PatientInfo, RateLimiter, build_context
from ai.agent.session_store import InMemorySessionStore
from ai.agent.tools.booking_store import BookingStore
from ai.llm.client import LLMResponse, ToolCall
from ai.llm.retry import AllProvidersFailed

T0 = datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc)
ME = PatientInfo("demo-patient-2", "Asia/Taipei")
OTHER = PatientInfo("demo-patient-3", "UTC")
FULL = {"hospital_id": 9002, "preferred_slots": ["2026-12-04 10:00"], "language": "en", "inquiry": "scar laser options",
        "nationality": "TW", "visa_needed": False}


class Clock:
    def __init__(self):
        self.now = T0

    def __call__(self):
        return self.now


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


def make(script, **kw):
    clock = kw.pop("clock", None) or Clock()
    llm = ScriptLLM(script)
    sessions = kw.pop("sessions", None) or InMemorySessionStore(clock)
    bookings = kw.pop("bookings", None) or BookingStore()
    service = ChatService(llm, sessions=sessions, bookings=bookings, clock=clock, **kw)
    return service, llm, sessions, bookings, clock


def system_prompt(llm, call_index=0):
    return llm.calls[call_index][0]["content"]


# ------------------------------------------------------------------ 기본 대화와 저장
def test_first_ask_creates_session_and_stores_only_masked_text():
    service, llm, sessions, _, _ = make([say("Hello!")])
    r = service.ask(ME, None, "Hi, my email is kim.test@example.com", "en")
    assert r.text == "Hello!" and r.cards == [] and r.ai_generated and not r.blocked
    s = sessions.get(ME.patient_id, r.session_id)
    assert s.title == "Hi, my email is [email]" and s.lang == "en"
    msgs = sessions.messages(s.id, 10)
    assert [(m.role, m.content) for m in msgs] == [("user", "Hi, my email is [email]"), ("assistant", "Hello!")]
    assert "example.com" not in str([m.content for m in msgs]) + s.title


def test_stored_conversation_is_text_only_and_state_restores_shown_hospitals():
    service, llm, sessions, _, _ = make([
        call("search_hospitals", {"department": "피부과", "district": "수성구", "language": "en"}),
        say("Two clinics found."),
        say("Clinic A it is."),
    ])
    r1 = service.ask(ME, None, "acne scars in Suseong-gu, English", "en")
    assert [c.type for c in r1.cards] == ["hospital_list"]
    stored = sessions.messages(r1.session_id, 10)
    assert [m.role for m in stored] == ["user", "assistant"]  # 도구 호출·결과·카드는 저장하지 않음
    assert sessions.get(ME.patient_id, r1.session_id).state["shown_hospitals"] == [
        {"id": 9001, "name": "Demo Dermatology Clinic A"}, {"id": 9002, "name": "Demo Dermatology Clinic B"}]

    service.ask(ME, r1.session_id, "the first one please", "en")
    third_call = llm.calls[2]  # 두 번째 ask의 첫 LLM 호출
    ctx = third_call[0]["content"]
    assert "1. Demo Dermatology Clinic A (id 9001)" in ctx and "2. Demo Dermatology Clinic B (id 9002)" in ctx
    assert [m["role"] for m in third_call[1:]] == ["user", "assistant", "user"]  # 이전 대화는 텍스트만 다시 들어감
    assert not any(m["role"] == "tool" for m in third_call)


def test_other_patients_cannot_read_or_delete_a_session():
    service, _, sessions, _, _ = make([say("hi"), say("never")])
    r = service.ask(ME, None, "hello", "en")
    with pytest.raises(ChatServiceError) as e:
        service.ask(OTHER, r.session_id, "hello", "en")
    assert (e.value.status, e.value.code) == (404, "not_found")
    with pytest.raises(ChatServiceError) as e2:
        service.delete_session(OTHER, r.session_id)
    assert e2.value.status == 404 and sessions.get(ME.patient_id, r.session_id) is not None
    service.delete_session(ME, r.session_id)
    assert sessions.get(ME.patient_id, r.session_id) is None
    with pytest.raises(ChatServiceError):
        service.delete_session(ME, r.session_id)


# ------------------------------------------------------------------ 입력 검사
def test_input_validation_and_language_aliases():
    service, llm, *_ = make([say("ok"), say("ok")])
    for bad in ("", "   ", "x" * 1001):
        with pytest.raises(ChatServiceError) as e:
            service.ask(ME, None, bad, "en")
        assert (e.value.status, e.value.code) == (422, "validation")
    with pytest.raises(ChatServiceError) as e:
        service.ask(ME, None, "hi", "ja")  # 프론트·백엔드가 지원하지 않는 언어
    assert e.value.code == "validation" and "zh-CN" in e.value.detail["supported"]
    service.ask(ME, None, "你好", "zh")  # 옛 코드는 zh-CN으로
    assert "language=zh-CN" in system_prompt(llm)
    assert svc.normalize_language("zh-Hant") == "zh-TW"
    assert len(llm.script) == 1 and len(llm.calls) == 1  # 검증 실패 3번 + 언어 오류 1번에서는 LLM을 부르지 않았다


# ------------------------------------------------------------------ 호출 제한
def test_rate_limit_per_minute_per_patient_and_window_resets():
    clock = Clock()
    service, *_ = make([say("a")] * 8, clock=clock, limiter=RateLimiter(per_minute=2, per_day=100))
    service.ask(ME, None, "one", "en")
    service.ask(ME, None, "two", "en")
    with pytest.raises(ChatServiceError) as e:
        service.ask(ME, None, "three", "en")
    assert (e.value.status, e.value.code) == (429, "rate_limited") and e.value.detail["retry_after"] > 0
    service.ask(OTHER, None, "other patient is not limited", "en")
    clock.now += timedelta(seconds=61)
    service.ask(ME, None, "again", "en")


def test_daily_limit_and_session_cap(monkeypatch):
    clock = Clock()
    service, *_ = make([say("a")] * 6, clock=clock, limiter=RateLimiter(per_minute=100, per_day=2))
    service.ask(ME, None, "one", "en")
    service.ask(ME, None, "two", "en")
    with pytest.raises(ChatServiceError) as e:
        service.ask(ME, None, "three", "en")
    assert e.value.detail["limit"] == "day"
    monkeypatch.setattr(svc, "MAX_SESSIONS_PER_PATIENT", 1)
    service2, *_ = make([say("a")] * 3)
    service2.ask(ME, None, "first session", "en")
    with pytest.raises(ChatServiceError) as e2:
        service2.ask(ME, None, "second session", "en")
    assert e2.value.detail["limit"] == "sessions"


# ------------------------------------------------------------------ 실패와 응급
def test_all_llm_providers_failing_gives_503_and_leaves_no_session():
    service, _, sessions, *_ = make([AllProvidersFailed([])])
    with pytest.raises(ChatServiceError) as e:
        service.ask(ME, None, "hello", "en")
    assert (e.value.status, e.value.code) == (503, "chatbot.unavailable")
    assert "모든 LLM" not in e.value.message and sessions.count(ME.patient_id) == 0


def test_emergency_is_blocked_and_stored_without_the_original_text():
    service, llm, sessions, *_ = make([])
    r = service.ask(PatientInfo("demo-patient-2"), None, "수술 부위에서 피가 멈추지 않아요", "ko")
    assert r.blocked and not r.ai_generated and "119" in r.text and llm.calls == []
    s = sessions.get("demo-patient-2", r.session_id)
    assert s.title == "[emergency message]"
    assert sessions.messages(s.id, 5)[0].content == "[emergency message]" and sessions.messages(s.id, 5)[0].refused


# ------------------------------------------------------------------ 요청서: 사람이 쓰는 것과 같은 API로 제출
def test_submission_through_the_existing_api_is_noticed_on_the_next_turn():
    service, llm, sessions, bookings, _ = make([
        call("prepare_booking_request", FULL), say("Check the card and press Submit."),
        say("It was sent. The hospital will confirm."),
    ])
    # 체류 형태를 이미 말한 세션
    s = sessions.create(ME.patient_id, "en", "t", {"residency": "short_term"})
    r1 = service.ask(ME, s.id, "Book clinic B on Dec 4 10:00, I'm from Taiwan, no visa help, about scar laser options", "en")
    card = next(c for c in r1.cards if c.type == "booking_draft").data
    assert card.hospital_id == 9002 and card.consents_required == ["privacy", "overseas_transfer"]
    assert card.request["department_code"] == "dermatology" and card.request["preferred_slots"] == ["2026-12-04T01:00:00Z"]
    assert card.request["patient_timezone"] == "Asia/Taipei" and card.request["lang"] == "en"
    state = sessions.get(ME.patient_id, s.id).state
    assert state["draft"]["hospital_id"] == 9002 and state["draft_known_booking_ids"] == []

    # 제출 전에 물으면 아직 초안이 열려 있다고 알려 줌
    ctx = build_context(state, None)
    assert "NOT submitted yet" in ctx and "scar laser" not in ctx  # 사용자가 쓴 문의 내용은 시스템 맥락에 넣지 않는다

    # 프론트가 사람이 쓰는 요청서와 같은 호출을 한다: request + 동의
    consents = [{"kind": k, "version": "v1"} for k in card.consents_required]
    booking = bookings.create_from_payload(ME.patient_id, card.hospital_id, card.request, consents, today=T0)
    assert booking["status"] == "pending"

    r2 = service.ask(ME, s.id, "Did it go through?", "en")
    ctx2 = system_prompt(llm, 2)
    assert f"id {booking['id']}, status pending" in ctx2 and "draft is closed" in ctx2
    state2 = sessions.get(ME.patient_id, s.id).state
    assert "draft" not in state2 and "draft_known_booking_ids" not in state2
    assert r2.text.startswith("It was sent")

    # 그다음 턴에는 제출 알림이 다시 나오지 않는다
    service.orchestrator.llm.script.append(say("Anything else?"))
    service.ask(ME, s.id, "thanks", "en")
    assert "submitted the request" not in system_prompt(llm, 3)


def test_existing_open_request_before_the_draft_is_not_mistaken_for_a_submission():
    # demo-patient-1은 9001에 이미 pending 요청이 있다. 같은 병원에 초안을 만들어도 그 요청은 '새 요청'이 아니다
    one = PatientInfo("demo-patient-1", "UTC")
    service, llm, sessions, bookings, _ = make([
        call("prepare_booking_request", {**FULL, "hospital_id": 9001}), say("Check the card."), say("Still a draft."),
    ])
    s = sessions.create(one.patient_id, "en", "t", {"residency": "short_term"})
    service.ask(one, s.id, "book clinic A", "en")
    state = sessions.get(one.patient_id, s.id).state
    assert state["draft_known_booking_ids"] == ["demo-bk-001", "demo-bk-002"]  # 환자의 기존 요청 전부(가상 2건)
    service.ask(one, s.id, "ok", "en")
    assert "NOT submitted yet" in system_prompt(llm, 2) and "submitted the request" not in system_prompt(llm, 2)
    assert "draft" in sessions.get(one.patient_id, s.id).state


def test_changing_to_another_hospital_replaces_the_draft_and_snapshot():
    service, _, sessions, bookings, _ = make([
        call("prepare_booking_request", FULL), say("draft B"),
        call("prepare_booking_request", {**FULL, "hospital_id": 9001}), say("draft A"),
    ])
    s = sessions.create(ME.patient_id, "en", "t", {"residency": "short_term"})
    service.ask(ME, s.id, "clinic B", "en")
    service.ask(ME, s.id, "actually clinic A", "en")
    assert sessions.get(ME.patient_id, s.id).state["draft"]["hospital_id"] == 9001


# ------------------------------------------------------------------ 보관 기간과 탈퇴
def test_purge_after_retention_and_withdrawal_delete():
    clock = Clock()
    service, _, sessions, *_ = make([say("a"), say("b")], clock=clock)
    old = service.ask(ME, None, "old chat", "en").session_id
    clock.now += timedelta(days=20)
    recent = service.ask(ME, None, "recent chat", "en").session_id
    clock.now += timedelta(days=15)  # old는 35일, recent는 15일
    assert service.purge_expired() == 1
    assert sessions.get(ME.patient_id, old) is None and sessions.get(ME.patient_id, recent) is not None
    assert sessions.delete_all_for_patient(ME.patient_id) == 1 and sessions.count(ME.patient_id) == 0


# ------------------------------------------------------------------ 카드 모델
def test_every_tool_result_fits_its_card_model():
    """도구가 칸을 바꾸면 카드가 조용히 사라진다 → 이 테스트가 먼저 알려 준다."""
    cases = [
        ("search_hospitals", {"department": "피부과"}, "hospital_list"),
        ("recommend_hospitals", {"department": "피부과", "language": "en"}, "hospital_suggestions"),
        ("get_hospital", {"hospital_id": 9001}, "hospital_detail"),
        ("get_prices", {"item": "scar"}, "price_list"),
        ("retrieve_docs", {"query": "visa", "topic": "visa"}, "sources"),
        ("check_availability", {"hospital_id": 9001, "date_from": "2026-12-01", "date_to": "2026-12-03"}, "time_slots"),
        ("get_my_bookings", {}, "booking_list"),
        ("open_aftercare_thread", {"booking_id": "demo-bk-002", "topic": "documents", "message": "receipt"}, "aftercare_thread"),
        ("prepare_booking_request", FULL, "booking_draft"),
    ]
    for tool, args, card_type in cases:
        service, _, sessions, *_ = make([call(tool, args), say("done")])
        s = sessions.create("demo-patient-1" if tool in ("get_my_bookings", "open_aftercare_thread") else ME.patient_id, "en", "t",
                            {"residency": "short_term"})
        who = PatientInfo(s.patient_id, "UTC")
        r = service.ask(who, s.id, "go", "en")
        assert [c.type for c in r.cards] == [card_type], tool
