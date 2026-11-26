"""챗봇 병원 찾기·상세가 실제 병원 DB(hospital.service)를 쓰는지 — POST /chatbot/ask로만 확인. 가짜 LLM.

조건 맞춤 제안·예약은 아직 가상 병원(9001~) 그대로 (2026-11-17 결정: 찾기·상세만 연결).
공개는 등록 병원만 (결정 21) → 챗봇이 `registered_only=False`로 불러도 미등록 병원은 나오지 않음.
실제 병원은 응대 언어 정보가 없으므로 언어로 거르지 않고 "병원에 확인" 안내를 붙인다.
"""

from test_auth_patient import auth, signup
from test_chatbot_api import ASK, call, llm, say  # noqa: F401 — llm은 fixture
from test_hospitals import files, hosp, load  # noqa: F401 — files는 fixture


def seed(db_engine, files):
    load(db_engine, **files(
        [hosp("Y1", "등록피부과의원", sgguCdNm="대구수성구"), hosp("Y2", "미등록피부과의원", sgguCdNm="대구수성구"),
         hosp("Y3", "중구성형외과의원", sgguCdNm="대구중구")],
        registered=[{"registration_no": "M-1", "name_en": "Registered Derm Clinic", "ykiho": "Y1"}],
        hours=[{"ykiho": "Y1", "has_dermatology": "Y", "trmtMonStart": "0930", "trmtMonEnd": "1830",
                "trmtSatStart": "0930", "trmtSatEnd": "1400", "noTrmtSun": "전부 휴무"},
               {"ykiho": "Y2", "has_dermatology": "Y"}, {"ykiho": "Y3", "has_plastic_surgery": "Y"}],
    ))


def cards(r):
    assert r.status_code == 200, r.text
    return {c["type"]: c["data"] for c in r.json()["cards"]}


def test_병원_찾기는_실제_DB_기본은_등록_병원만(client, db_engine, files, llm):
    seed(db_engine, files)
    token = signup(client)
    llm.script += [call("search_hospitals", {"department": "피부과", "district": "수성구", "language": "en"}),
                   say("One registered clinic.")]

    data = cards(client.post(ASK, headers=auth(token), json={"message": "dermatology in Suseong-gu"}))["hospital_list"]

    assert [h["name_ko"] for h in data["hospitals"]] == ["등록피부과의원"]
    h = data["hospitals"][0]
    assert (h["hospital_id"], h["name_en"], h["district"], h["departments"]) == (1, "Registered Derm Clinic", "수성구", ["피부과"])
    assert h["is_registered_facility"] is True and h["staff_languages"] == []
    assert "language" in data["note"].lower()  # 언어 정보가 없음을 알림 (언어로 거르지 않음)


def test_registered_only_false여도_미등록_병원은_안_나오고_요일_필터는_진료시간으로(client, db_engine, files, llm):
    seed(db_engine, files)
    token = signup(client)
    llm.script += [call("search_hospitals", {"department": "피부과", "registered_only": False}), say("One."),
                   call("search_hospitals", {"department": "피부과", "registered_only": False, "open_on": "sat"}), say("One.")]

    first = cards(client.post(ASK, headers=auth(token), json={"message": "all dermatology"}))["hospital_list"]
    sat = cards(client.post(ASK, headers=auth(token), json={"message": "open on Saturday"}))["hospital_list"]

    assert [h["name_ko"] for h in first["hospitals"]] == ["등록피부과의원"]
    assert [h["name_ko"] for h in sat["hospitals"]] == ["등록피부과의원"]


def test_병원_상세는_실제_진료시간_미등록_병원은_없는_병원처럼(client, db_engine, files, llm):
    seed(db_engine, files)
    token = signup(client)
    llm.script += [call("get_hospital", {"hospital_id": 1}), say("Details."),
                   call("get_hospital", {"hospital_id": 2}), say("Details."),
                   call("get_hospital", {"hospital_id": 999}), say("Not found.")]

    d1 = cards(client.post(ASK, headers=auth(token), json={"message": "hospital 1"}))["hospital_detail"]
    d2 = cards(client.post(ASK, headers=auth(token), json={"message": "hospital 2"}))
    missing = cards(client.post(ASK, headers=auth(token), json={"message": "hospital 999"}))

    assert d1["hours"]["mon"] == "09:30-18:30" and d1["hours"]["sat"] == "09:30-14:00"
    assert d1["hours"]["sun"] is None  # 일요일 휴무가 확인된 경우만 None
    assert "tue" not in d1["hours"]  # 시간 정보 없음 → 휴진(None)으로 보이지 않게 뺌
    # 등록·영업 중이어도 메디대구에 입점하지 않은 실제 병원은 챗봇으로 요청 불가 (결정 31, 2026-11-26 수정)
    assert d1["can_request_consultation"] is False and d1["tel"] == "053-000-0000"
    assert d1["hours_source"] != "demo"
    assert d2 == {}  # 미등록 병원 = 없는 병원과 같게 (카드 없음)
    assert missing == {}  # 없는 병원은 도구 오류 → 카드 없음


# ---------- 조건 맞춤 제안·예약 = 메디대구 입점 가상 병원만 (결정 31) ----------

VISITOR = {"country": "TW", "alien_registration": False, "domestic_residence": False, "health_insurance": False}


def _visitor(client):
    token = signup(client)
    assert client.put("/api/v1/me/residency", json=VISITOR, headers=auth(token)).status_code == 200
    return token


def _tool_result(llm, name):
    import json

    msgs = [m for m in llm.calls[-1] if m["role"] == "tool"]
    return json.loads(msgs[-1]["content"])


def test_조건_맞춤_제안은_입점_가상_병원만_실제_병원은_안_나옴(client, db_engine, files, llm):
    from sqlalchemy.orm import Session

    from db_rows import demo_partner

    seed(db_engine, files)  # 실제(등록) 피부과 Y1
    with Session(db_engine) as s:
        demo_partner(s, 9002)
    token = _visitor(client)
    llm.script += [call("recommend_hospitals", {"department": "피부과", "open_on": "mon"}), say("Here are options.")]
    data = cards(client.post(ASK, headers=auth(token), json={"message": "where for acne scars?"}))["hospital_suggestions"]
    assert [h["hospital_id"] for h in data["suggestions"]] == [9002]


def test_실제_등록_병원은_예약_초안을_만들지_않음(client, db_engine, files, llm):
    seed(db_engine, files)
    token = _visitor(client)
    llm.script += [call("prepare_booking_request", {"hospital_id": 1, "department": "피부과", "preferred_slots": ["2026-12-04 10:00"],
                                                    "language": "en", "nationality": "TW", "visa_needed": False, "visa_statement": "no visa help", "inquiry": "price?"}),
                   say("Sorry.")]
    r = client.post(ASK, headers=auth(token), json={"message": "book Y1, no visa help"})
    assert "booking_draft" not in cards(r)
    out = _tool_result(llm, "prepare_booking_request")
    assert out["status"] == "not_available" and "not joined" in out["reason"]


def test_가상_병원_예약_가능_시간은_진료_시간에서(client, db_engine, llm):
    from sqlalchemy.orm import Session

    from db_rows import demo_partner

    with Session(db_engine) as s:
        demo_partner(s, 9002)
    token = _visitor(client)
    llm.script += [call("check_availability", {"hospital_id": 9002, "date_from": "2026-12-05", "date_to": "2026-12-06"}),
                   say("Saturday works.")]
    client.post(ASK, headers=auth(token), json={"message": "when can I go?"})
    slots = _tool_result(llm, "check_availability")["slots"]
    assert slots == {"2026-12-05": ["10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00"]}  # 일요일(12-06) 휴진


def test_챗봇_요청서_카드는_그대로_예약_API로_보낼_수_있다(client, db_engine, llm):
    """카드의 request + 환자가 체크한 동의 = 사람이 쓰는 요청서와 같은 API (결정 3). 계약 필수 칸이 빠지면 422가 나던 것."""
    from sqlalchemy.orm import Session

    from db_rows import demo_partner

    with Session(db_engine) as s:
        demo_partner(s, 9002)
    token = _visitor(client)
    llm.script += [call("prepare_booking_request", {"hospital_id": 9002, "department": "피부과", "preferred_slots": ["2030-12-05 10:00"],
                                                    "language": "ko", "nationality": "TW", "visa_needed": False, "visa_statement": "no visa help",
                                                    "inquiry": "레이저 몇 번?"}), say("Check the card.")]
    card = cards(client.post(ASK, headers=auth(token), json={"message": "book 9002, no visa help"}))["booking_draft"]
    consents = [{"kind": k, "version": "2026-11-03" if k == "privacy" else "2026-11-18"} for k in card["consents_required"]]
    r = client.post(f"/api/v1/hospitals/{card['hospital_id']}/booking-requests", headers=auth(token),
                    json={**card["request"], "consents": consents})
    assert r.status_code == 201, r.json()
    assert r.json()["status"] == "pending" and r.json()["hospital_id"] == 9002


def test_입점_가상_병원만_상세에_요청_가능_목록에도_응대_언어(client, db_engine, llm):
    from sqlalchemy.orm import Session

    from db_rows import demo_partner
    from modules.chatbot.hospitals import _demo_extra

    with Session(db_engine) as s:
        demo_partner(s, 9002)
    token = _visitor(client)
    llm.script += [call("get_hospital", {"hospital_id": 9002}), say("Details."),
                   call("search_hospitals", {"department": "피부과"}), say("List.")]
    d = cards(client.post(ASK, headers=auth(token), json={"message": "9002"}))["hospital_detail"]
    assert d["can_request_consultation"] is True
    listed = _tool_result(llm, "get_hospital")  # noqa: F841 — 상세 확인용
    client.post(ASK, headers=auth(token), json={"message": "dermatology"})
    h = next(x for x in _tool_result(llm, "search_hospitals")["hospitals"] if x["hospital_id"] == 9002)
    extra = _demo_extra().get(9002, {})
    assert h["staff_languages"] == extra.get("staff_languages", []) and h["ai_translation_chat"] == extra.get("ai_translation_chat", False)


def test_가상_병원_휴진일_희망_일시는_초안_없이_후보만(client, db_engine, llm):
    from sqlalchemy.orm import Session

    from db_rows import demo_partner

    with Session(db_engine) as s:
        demo_partner(s, 9002)
    token = _visitor(client)
    llm.script += [call("prepare_booking_request", {"hospital_id": 9002, "department": "피부과", "preferred_slots": ["2030-12-08 10:00"],
                                                    "language": "en", "nationality": "TW", "visa_needed": False, "visa_statement": "no visa help",
                                                    "inquiry": "x"}), say("Closed that day.")]
    r = client.post(ASK, headers=auth(token), json={"message": "book 9002 Sunday, no visa help"})
    assert "booking_draft" not in cards(r)
    out = _tool_result(llm, "prepare_booking_request")
    assert out["status"] == "needs_info" and out["closed_slots"] == ["2030-12-08 10:00"]  # 2030-12-08 = 일요일
    assert out["open_candidates"] == {"2030-12-08": []}
