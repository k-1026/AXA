"""챗봇 병원 찾기·상세가 실제 병원 DB(hospital.service)를 쓰는지 — POST /chatbot/ask로만 확인. 가짜 LLM.

조건 맞춤 제안·예약은 아직 가상 병원(9001~) 그대로 (2026-11-17 결정: 찾기·상세만 연결).
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


def test_등록_안_된_병원도_찾을_수_있고_요일_필터는_진료시간으로(client, db_engine, files, llm):
    seed(db_engine, files)
    token = signup(client)
    llm.script += [call("search_hospitals", {"department": "피부과", "registered_only": False}), say("Two."),
                   call("search_hospitals", {"department": "피부과", "registered_only": False, "open_on": "sat"}), say("One.")]

    first = cards(client.post(ASK, headers=auth(token), json={"message": "all dermatology"}))["hospital_list"]
    sat = cards(client.post(ASK, headers=auth(token), json={"message": "open on Saturday"}))["hospital_list"]

    assert sorted(h["name_ko"] for h in first["hospitals"]) == ["등록피부과의원", "미등록피부과의원"]
    assert [h["name_ko"] for h in sat["hospitals"]] == ["등록피부과의원"]


def test_병원_상세는_실제_진료시간_상담_가능은_등록_병원만(client, db_engine, files, llm):
    seed(db_engine, files)
    token = signup(client)
    llm.script += [call("get_hospital", {"hospital_id": 1}), say("Details."),
                   call("get_hospital", {"hospital_id": 2}), say("Details."),
                   call("get_hospital", {"hospital_id": 999}), say("Not found.")]

    d1 = cards(client.post(ASK, headers=auth(token), json={"message": "hospital 1"}))["hospital_detail"]
    d2 = cards(client.post(ASK, headers=auth(token), json={"message": "hospital 2"}))["hospital_detail"]
    missing = cards(client.post(ASK, headers=auth(token), json={"message": "hospital 999"}))

    assert d1["hours"]["mon"] == "09:30-18:30" and d1["hours"]["sat"] == "09:30-14:00"
    assert d1["hours"]["sun"] is None  # 일요일 휴무가 확인된 경우만 None
    assert "tue" not in d1["hours"]  # 시간 정보 없음 → 휴진(None)으로 보이지 않게 뺌
    assert d1["can_request_consultation"] is True and d1["tel"] == "053-000-0000"
    assert d1["hours_source"] != "demo"
    assert d2["can_request_consultation"] is False
    assert missing == {}  # 없는 병원은 도구 오류 → 카드 없음
