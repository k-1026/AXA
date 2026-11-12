"""6단계: 가짜 예약 저장소와 제출 흐름 (오케스트레이터 submit_draft)."""

from datetime import date, datetime, timezone

import pytest

from ai.agent.core.orchestrator import ConversationState, Orchestrator
from ai.agent.tools.booking_store import BookingError, BookingStore, required_consents, to_utc_iso
from ai.agent.tools.chat_tools import build_registry
from ai.llm.client import LLMResponse, ToolCall

NOW = datetime(2026, 11, 10, tzinfo=timezone.utc)
CONSENTS = [{"kind": "privacy", "version": "v1"}, {"kind": "overseas_transfer", "version": "v1"}]


def draft(**kw):
    d = {"hospital_id": 9001, "hospital_name_en": "Demo Dermatology Clinic A", "department": "피부과", "department_code": "dermatology",
         "preferred_slots": ["2026-12-01 10:00"], "language": "en", "nationality": "TW", "visa_needed": False,
         "contact_method": "email", "inquiry": "scar laser options"}
    d.update(kw)
    return d


def create(store, patient="demo-patient-2", d=None, consents=CONSENTS, residency="short_term", **kw):
    return store.create_request(patient, d or draft(), consents, residency=residency,
                                patient_timezone="Asia/Taipei", today=NOW, **kw)


def code(fn):
    with pytest.raises(BookingError) as e:
        fn()
    return e.value.code


def test_create_pending_in_backend_shape_with_utc_slots():
    store = BookingStore()
    row = create(store)
    assert row["status"] == "pending" and row["hospital_name_en"] == "Demo Dermatology Clinic A"
    req = row["request"]
    assert req["preferred_slots"] == ["2026-12-01T01:00:00Z"]  # 10:00 KST = 01:00 UTC
    assert req["patient_timezone"] == "Asia/Taipei" and req["lang"] == "en" and req["nationality"] == "TW"
    assert req["message"] == "scar laser options" and req["visa_needed"] is False and req["contact_method"] == "email"
    assert [c["kind"] for c in row["consents"]] == ["privacy", "overseas_transfer"]
    assert [r["status"] for r in store.list_for_patient("demo-patient-2")] == ["pending"]
    assert to_utc_iso("2026-12-01 00:30") == "2026-11-30T15:30:00Z"


def test_submit_rules_use_backend_error_codes():
    store = BookingStore()
    assert code(lambda: create(store, patient=None)) == "auth.required"
    assert code(lambda: create(store, residency="resident")) == "booking.not_available"
    assert code(lambda: create(store, residency=None)) == "validation"
    assert code(lambda: create(store, d=draft(hospital_id=9006))) == "booking.not_available"  # 미등록
    assert code(lambda: create(store, d=draft(hospital_id=1))) == "not_found"
    assert code(lambda: create(store, d=draft(nationality=""))) == "validation"
    d = draft()
    del d["visa_needed"]
    assert code(lambda: create(store, d=d)) == "validation"
    assert code(lambda: create(store, d=draft(preferred_slots=[]))) == "validation"
    assert code(lambda: create(store, d=draft(preferred_slots=["2026-12-0%d 10:00" % i for i in range(1, 5)]))) == "validation"
    assert code(lambda: create(store, d=draft(preferred_slots=["2026-11-01 10:00"]))) == "validation"  # 지난 일시
    assert store.list_for_patient("demo-patient-2") == []  # 실패한 시도는 아무것도 만들지 않음


def test_consents_required_by_kind():
    assert required_consents(draft()) == ["privacy", "overseas_transfer"]
    assert required_consents(draft(language="ko")) == ["privacy"]
    assert required_consents(draft(health_info="x")) == ["privacy", "health", "overseas_transfer"]
    store = BookingStore()
    with pytest.raises(BookingError) as e:
        create(store, consents=[{"kind": "privacy", "version": "v1"}])
    assert e.value.code == "consent.required" and e.value.detail["missing"] == ["overseas_transfer"]
    assert code(lambda: create(store, consents=[{"kind": "privacy", "version": ""}, {"kind": "overseas_transfer", "version": "v1"}])) == "consent.required"
    assert code(lambda: create(store, d=draft(health_info="scars"), consents=CONSENTS)) == "consent.required"  # health 동의 없음
    ok = create(store, d=draft(health_info="scars"), consents=CONSENTS + [{"kind": "health", "version": "v1"}])
    assert ok["request"]["health_info"] == "scars"


def test_duplicate_open_request_to_same_hospital():
    store = BookingStore()
    first = create(store)
    assert code(lambda: create(store)) == "booking.duplicate"
    other_hospital = create(store, d=draft(hospital_id=9002, hospital_name_en="Demo Dermatology Clinic B"))
    assert other_hospital["status"] == "pending"
    store.patient_respond("demo-patient-2", first["id"], "cancel")
    assert create(store)["status"] == "pending"  # 취소 후에는 다시 가능


def test_seed_pending_blocks_same_patient_same_hospital():
    store = BookingStore()
    assert code(lambda: create(store, patient="demo-patient-1")) == "booking.duplicate"  # demo-bk-001이 pending


def test_status_transitions_follow_contract():
    store = BookingStore()
    bk = create(store)["id"]
    assert store.hospital_respond(bk, "propose", slot="2026-12-02 11:00")["status"] == "proposed"
    assert code(lambda: store.hospital_respond(bk, "confirm")) == "booking.invalid_transition"  # proposed → confirm 없음
    done = store.patient_respond("demo-patient-2", bk, "accept")
    assert done["status"] == "confirmed" and done["confirmed_slot"] == "2026-12-02 11:00"
    assert code(lambda: store.patient_respond("demo-patient-2", bk, "cancel")) == "booking.invalid_transition"
    assert code(lambda: store.patient_respond("demo-patient-1", bk, "cancel")) == "not_found"  # 남의 예약은 404
    bk2 = create(store, d=draft(hospital_id=9002))["id"]
    assert store.hospital_respond(bk2, "reject")["status"] == "rejected"
    bk3 = create(store, d=draft(hospital_id=9003, hospital_name_en="Demo Plastic Surgery Clinic"))["id"]
    confirmed = store.hospital_respond(bk3, "confirm")
    assert confirmed["status"] == "confirmed" and confirmed["confirmed_slot"] == "2026-12-01 10:00"
    assert [e["status"] for e in confirmed["events"]] == ["pending", "confirmed"]


# ------------------------------------------------------------------ 오케스트레이터 제출
class ScriptLLM:
    def __init__(self, script):
        self.script, self.calls = list(script), []

    def chat(self, messages, *, tools=None, service="chatbot", **kw):
        self.calls.append(messages)
        return self.script.pop(0)


def say(text):
    return LLMResponse(text=text, tool_calls=[], provider="fake", model="fake")


def call(name, args):
    return LLMResponse(text=None, tool_calls=[ToolCall(id="c1", name=name, arguments=args)], provider="fake", model="fake")


def test_chat_to_pending_end_to_end_with_hospital_confirm():
    full = {"hospital_id": 9001, "preferred_slots": ["2026-12-01 10:00"], "language": "en", "inquiry": "scar laser options",
            "nationality": "TW", "visa_needed": False}
    llm = ScriptLLM([
        call("prepare_booking_request", full), say("Check the card, tick the consents and press Submit."),
        call("get_my_bookings", {}), say("Your request to Clinic A is pending."),
        call("get_my_bookings", {}), say("Confirmed for Dec 1."),
    ])
    orch = Orchestrator(llm, build_registry(), today=lambda: date(2026, 11, 10))
    state = ConversationState(patient_id="demo-patient-2", residency="short_term", timezone="Asia/Taipei")

    reply = orch.handle(state, "Book Clinic A on Dec 1 at 10:00, I'm from Taiwan, no visa help needed")
    assert [c["type"] for c in reply.cards] == ["booking_draft"] and state.booking_draft is not None
    assert orch.store.list_for_patient("demo-patient-2") == []  # 챗봇은 제출하지 않았다

    # 동의 없이 [제출] → 거절, 초안은 그대로
    bad = orch.submit_draft(state, [{"kind": "privacy", "version": "v1"}])
    assert not bad.ok and bad.error["code"] == "consent.required" and state.booking_draft is not None
    # 환자가 동의하고 [제출]
    res = orch.submit_draft(state, CONSENTS)
    assert res.ok and res.booking["status"] == "pending" and state.booking_draft is None
    assert state.history[-1]["role"] == "assistant" and "[Submitted]" in state.history[-1]["content"]
    # 두 번 제출 불가 (초안이 비어 있음)
    assert orch.submit_draft(state, CONSENTS).error["code"] == "validation"

    status = orch.handle(state, "How is my request?")
    booking_card = status.cards[0]["data"]["bookings"][0]
    assert booking_card["status"] == "pending" and booking_card["hospital_id"] == 9001
    assert "request" not in booking_card and "consents" not in booking_card  # 요청서 원문·동의는 모델에 보내지 않음

    orch.store.hospital_respond(res.booking["id"], "confirm")  # 병원 직원이 대시보드에서 확정
    done = orch.handle(state, "And now?")
    assert done.cards[0]["data"]["bookings"][0]["status"] == "confirmed"
    # 제출 사실이 모델에게도 보였다
    assert any("[Submitted]" in str(m.get("content", "")) for m in llm.calls[2])


def test_submit_blocked_for_resident_and_anonymous():
    orch = Orchestrator(ScriptLLM([]), build_registry(), today=lambda: date(2026, 11, 10))
    state = ConversationState(patient_id=None, residency="short_term")
    state.booking_draft = draft()
    assert orch.submit_draft(state, CONSENTS).error["code"] == "auth.required"
    state.patient_id, state.residency = "demo-patient-2", "resident"
    assert orch.submit_draft(state, CONSENTS).error["code"] == "booking.not_available"
    assert state.booking_draft is not None and orch.store.list_for_patient("demo-patient-2") == []


def test_get_for_patient_returns_a_copy():
    from ai.agent.tools.booking_store import BookingStore
    store = BookingStore()
    row = store.get_for_patient("demo-patient-1", "demo-bk-001")
    row["status"] = "tampered"
    assert store.get_for_patient("demo-patient-1", "demo-bk-001")["status"] != "tampered"
