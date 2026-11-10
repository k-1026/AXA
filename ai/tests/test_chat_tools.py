"""ai/agent/tools 테스트 — 도구 정의·검증·가짜 응답 규칙."""

from ai.agent.tools.chat_tools import build_registry
from ai.agent.tools.registry import ToolContext

R = build_registry()
SHORT = ToolContext(patient_id="demo-patient-1", language="en", residency="short_term")


def test_tools_have_valid_specs():
    specs = R.openai_specs()
    assert len(specs) == 10
    for s in specs:
        fn = s["function"]
        assert s["type"] == "function" and fn["name"] and fn["description"]
        assert fn["parameters"]["type"] == "object"
    intents = {t.intent for t in R.tools.values()}
    assert intents == {"진료과안내", "병원찾기", "가격", "정보질문", "예약", "예약상태", "사후문의"}


def test_validation_errors_are_returned_not_raised():
    assert "problems" in R.run("search_hospitals", {}, SHORT)
    assert "problems" in R.run("search_hospitals", {"department": "피부과", "district": "강남구"}, SHORT)
    assert "problems" in R.run("get_hospital", {"hospital_id": "9001"}, SHORT)
    assert "problems" in R.run("search_hospitals", {"department": "피부과", "foo": 1}, SHORT)
    assert "available" in R.run("no_such_tool", {}, SHORT)
    assert "error" in R.run("get_hospital", {"hospital_id": 1}, SHORT)  # 없는 병원


def test_scar_flow_department_then_neutral_list():
    d = R.run("suggest_department", {"concern": "I have acne scars"}, SHORT)
    assert "피부과" in d["departments"] and "doctor" in d["note"]
    res = R.run("search_hospitals", {"department": "피부과", "district": "수성구", "language": "en"}, SHORT)
    names = [h["name_en"] for h in res["hospitals"]]
    assert names == sorted(names) and len(names) == 2  # 이름순, 미등록 C 제외
    assert all(h["is_registered_facility"] for h in res["hospitals"])
    assert "not a recommendation" in res["note"] and res["_demo"] is True


def test_translation_badge_filter():
    zh = R.run("search_hospitals", {"department": "피부과", "language": "zh"}, SHORT)["hospitals"]
    # B는 직원 중국어, A는 AI 번역 채팅으로 포함
    assert {h["hospital_id"] for h in zh} == {9001, 9002}
    dental_vi = R.run("search_hospitals", {"department": "치과", "language": "vi"}, SHORT)["hospitals"]
    assert dental_vi and dental_vi[0]["staff_languages"] == [] and dental_vi[0]["ai_translation_chat"] is True


def test_booking_draft_rules():
    args = {"hospital_id": 9001, "preferred_slots": ["2026-12-01 10:00"], "language": "en", "inquiry": "acne scars"}
    assert R.run("prepare_booking_request", args, ToolContext())["ask"] == "residency"
    res_resident = R.run("prepare_booking_request", args, ToolContext(residency="resident"))
    assert res_resident["status"] == "not_available" and "hospital_tel" in res_resident
    assert R.run("prepare_booking_request", {**args, "hospital_id": 9006}, SHORT)["status"] == "not_available"
    assert R.run("prepare_booking_request", {"hospital_id": 9001}, SHORT)["missing"] == ["preferred_slots", "language", "inquiry"]
    draft = R.run("prepare_booking_request", args, SHORT)
    assert draft["status"] == "draft" and draft["requires_patient_confirmation"] is True
    assert "health_information" in draft["consents_optional"]


def test_availability_and_dates():
    ok = R.run("check_availability", {"hospital_id": 9001, "date_from": "2026-12-01", "date_to": "2026-12-02"}, SHORT)
    assert set(ok["slots"]) == {"2026-12-01", "2026-12-02"}
    assert "error" in R.run("check_availability", {"hospital_id": 9001, "date_from": "12/01"}, SHORT)


def test_my_bookings_and_aftercare():
    assert R.run("get_my_bookings", {}, ToolContext())["status"] == "login_required"
    assert len(R.run("get_my_bookings", {}, SHORT)["bookings"]) == 2
    not_visited = R.run("open_aftercare_thread", {"booking_id": "demo-bk-001", "topic": "cost", "message": "receipt?"}, SHORT)
    assert not_visited["status"] == "not_available"
    opened = R.run("open_aftercare_thread", {"booking_id": "demo-bk-002", "topic": "documents", "message": "Need receipt"}, SHORT)
    assert opened["status"] == "opened" and "not medical" in opened["notice"]
    assert "problems" in R.run("open_aftercare_thread", {"booking_id": "demo-bk-002", "topic": "symptoms", "message": "x"}, SHORT)


def test_prices_and_docs():
    p = R.run("get_prices", {"item": "scar"}, SHORT)
    assert len(p["prices"]) == 2 and "Korean patients" in p["note"]
    assert R.run("retrieve_docs", {"query": "visa", "topic": "visa"}, SHORT)["documents"][0]["source"]
    assert R.run("retrieve_docs", {"query": "zzz unknown"}, SHORT)["documents"] == []
