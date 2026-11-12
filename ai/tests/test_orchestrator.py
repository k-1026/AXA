"""ai/agent/core/orchestrator.py 테스트 — 정해진 답을 차례로 내는 가짜 LLM 사용."""

from datetime import date

from ai.agent.core.orchestrator import ConversationState, Orchestrator, _trim
from ai.agent.tools.chat_tools import build_registry
from ai.llm.client import LLMResponse, ToolCall


class FakeLLM:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []  # (messages, tools)

    def chat(self, messages, *, tools=None, service="chatbot", **kw):
        self.calls.append((messages, tools))
        return self.script.pop(0)


def say(text):
    return LLMResponse(text=text, tool_calls=[], provider="fake", model="fake")


def call(*calls):
    return LLMResponse(
        text=None,
        tool_calls=[ToolCall(id=f"c{i}", name=n, arguments=a) for i, (n, a) in enumerate(calls)],
        provider="fake",
        model="fake",
    )


def make(script, **kw):
    llm = FakeLLM(script)
    return Orchestrator(llm, build_registry(), today=lambda: date(2026, 11, 10), **kw), llm


def test_plain_answer_keeps_history_and_ai_flag():
    orch, llm = make([say("Hello!")])
    state = ConversationState()
    reply = orch.handle(state, "hi")
    assert reply.text == "Hello!" and reply.ai_generated and reply.cards == [] and reply.trace == []
    assert [m["role"] for m in state.history] == ["user", "assistant"]
    system = llm.calls[0][0][0]
    assert system["role"] == "system" and "2026-11-10" in system["content"] and "residency=unknown" in system["content"]
    assert len(llm.calls[0][1]) == 11  # 도구 11개 전달


def test_tool_chain_builds_cards_from_tool_results():
    orch, llm = make([
        call(("suggest_department", {"concern": "acne scars"})),
        call(("search_hospitals", {"department": "피부과", "district": "수성구", "language": "en"})),
        say("Two clinics in Suseong-gu handle this."),
    ])
    state = ConversationState()
    reply = orch.handle(state, "I have acne scars, Suseong-gu, English")
    assert [t.name for t in reply.trace] == ["suggest_department", "search_hospitals"]
    assert [c["type"] for c in reply.cards] == ["hospital_list"]
    hospitals = reply.cards[0]["data"]["hospitals"]
    assert [h["hospital_id"] for h in hospitals] == [9001, 9002] and "_demo" not in reply.cards[0]["data"]
    # 대화 기록: user, assistant(tool_calls), tool, assistant(tool_calls), tool, assistant
    assert [m["role"] for m in state.history] == ["user", "assistant", "tool", "assistant", "tool", "assistant"]
    # 두 번째 LLM 호출에는 첫 도구 결과가 들어가 있어야 함
    assert llm.calls[1][0][-1]["role"] == "tool"


def test_residency_then_draft_is_stored_but_not_submitted():
    args = {"hospital_id": 9001, "preferred_slots": ["2026-12-01 10:00"], "language": "en", "inquiry": "acne scars",
            "nationality": "TW", "visa_needed": False}
    orch, _ = make([
        call(("prepare_booking_request", args)),
        say("Are you visiting short-term or living in Korea?"),
        call(("record_residency", {"residency": "short_term", "user_statement": "short-term visit"}),
             ("prepare_booking_request", args)),
        say("Please check the summary and press Submit."),
    ])
    state = ConversationState(patient_id="demo-patient-1")
    first = orch.handle(state, "Book clinic 9001 on Dec 1 10:00 about acne scars")
    assert first.cards == [] and state.booking_draft is None and state.residency is None
    second = orch.handle(state, "Short-term visit")
    assert state.residency == "short_term"
    assert [c["type"] for c in second.cards] == ["booking_draft"]
    assert state.booking_draft["hospital_id"] == 9001
    assert second.cards[0]["data"]["requires_patient_confirmation"] is True


def test_resident_gets_no_draft_card():
    args = {"hospital_id": 9001, "preferred_slots": ["2026-12-01 10:00"], "language": "en", "inquiry": "x",
            "nationality": "TW", "visa_needed": False}
    orch, _ = make([call(("prepare_booking_request", args)), say("Please call the hospital directly.")])
    state = ConversationState(residency="resident")
    reply = orch.handle(state, "book 9001")
    assert reply.cards == [] and state.booking_draft is None


def test_tool_error_goes_back_to_model_without_card():
    orch, llm = make([call(("search_hospitals", {"department": "피부과", "district": "강남구"})), say("Which district in Daegu?")])
    reply = orch.handle(ConversationState(), "강남구 피부과")
    assert reply.trace[0].ok is False and reply.cards == []
    assert "problems" in llm.calls[1][0][-1]["content"]


def test_step_limit_forces_answer_without_tools():
    loop = call(("get_hospital", {"hospital_id": 9001}))
    orch, llm = make([loop, loop, loop, say("Here is what I found so far.")], max_steps=2)
    state = ConversationState()
    reply = orch.handle(state, "tell me about 9001")
    assert reply.truncated and reply.text.startswith("Here is")
    assert llm.calls[-1][1] is None  # 마지막 호출은 도구 없이
    assert len(reply.trace) == 2
    assert state.history[-1]["role"] == "assistant" and "(system)" not in str(state.history)


def test_emergency_blocks_without_calling_llm():
    orch, llm = make([])
    state = ConversationState(language="ko")
    reply = orch.handle(state, "수술 부위에서 피가 멈추지 않아요")
    assert reply.blocked and "119" in reply.text and llm.calls == [] and reply.ai_generated is False
    assert reply.safety_categories == ["emergency"]
    assert "피가" not in str(state.history)  # 원문은 기록하지 않음


def test_guard_note_is_sent_this_turn_only():
    orch, llm = make([say("A doctor decides that at the consultation."), say("Sure.")])
    state = ConversationState()
    reply = orch.handle(state, "Is fractional laser safe for me?")
    assert reply.safety_categories == ["treatment_judgment"] and reply.medical_notice
    sent = llm.calls[0][0]
    assert sent[-2]["role"] == "system" and "Do not answer that part" in sent[-2]["content"] and sent[-1]["role"] == "user"
    assert all(m["role"] != "system" for m in state.history)
    orch.handle(state, "ok, show me clinics in Jung-gu")
    assert [m["role"] for m in llm.calls[1][0]].count("system") == 1  # 다음 턴에는 guard 없음


def test_pii_is_masked_before_llm_and_history():
    orch, llm = make([say("ok")])
    state = ConversationState()
    orch.handle(state, "My email is kim.test@example.com and phone 010-1234-5678")
    sent = llm.calls[0][0][-1]["content"]
    assert "example.com" not in sent and "1234" not in sent and "[email]" in sent and "[phone]" in sent
    assert "example.com" not in str(state.history)


def test_trim_cuts_only_at_user_boundaries():
    h = []
    for i in range(5):
        h += [{"role": "user", "content": f"u{i}"}, {"role": "assistant", "content": "", "tool_calls": [{}]},
              {"role": "tool", "content": "{}"}, {"role": "assistant", "content": f"a{i}"}]
    t = _trim(h, 9)
    assert t[0] == {"role": "user", "content": "u3"} and len(t) == 8
    assert _trim(h, 100) is h


def test_guessed_residency_is_rejected_by_code():
    args = {"hospital_id": 9001, "preferred_slots": ["2026-12-01 10:00"], "language": "en", "inquiry": "scar laser",
            "nationality": "TW", "visa_needed": False}
    orch, llm = make([
        # 사용자는 체류 형태를 말하지 않았는데 모델이 추측해서 기록하려는 경우
        call(("record_residency", {"residency": "short_term", "user_statement": "I am visiting short-term"}),
             ("prepare_booking_request", args)),
        say("Are you visiting short-term or living in Korea?"),
    ])
    state = ConversationState()
    reply = orch.handle(state, "10:00 please. I want to ask about scar laser options.")
    assert state.residency is None and state.booking_draft is None and reply.cards == []
    assert "not_recorded" in llm.calls[1][0][-2]["content"]


def test_recommendation_request_is_not_guarded_and_makes_card():
    orch, llm = make([
        call(("recommend_hospitals", {"department": "피부과", "district": "수성구", "language": "zh-CN"})),
        say("Clinic B has Chinese-speaking staff."),
    ])
    state = ConversationState(language="zh-CN", residency="short_term")
    reply = orch.handle(state, "给我推荐一家皮肤科")
    assert reply.safety_categories == [] and not reply.medical_notice
    assert [m["role"] for m in llm.calls[0][0]].count("system") == 1  # guard 지시 없음
    card = reply.cards[0]
    assert card["type"] == "hospital_suggestions" and card["data"]["suggestions"][0]["hospital_id"] == 9002
    assert "referral fee" in card["data"]["basis"]


def test_submit_draft_with_a_read_only_gateway_fails_with_a_clear_message():
    """서비스는 읽기 전용 게이트웨이를 주입한다. submit_draft(eval·시연 전용)를 잘못 부르면 AttributeError 대신 분명한 오류."""
    import pytest

    class ReadOnly:
        def list_for_patient(self, patient_id, status=None):
            return []

        def get_for_patient(self, patient_id, booking_id):
            raise KeyError(booking_id)

    orch = Orchestrator(None, build_registry(), store=ReadOnly())
    state = ConversationState(language="en", patient_id="p", residency="short_term", booking_draft={"hospital_id": 9001})
    with pytest.raises(NotImplementedError, match="booking-requests"):
        orch.submit_draft(state, [])
