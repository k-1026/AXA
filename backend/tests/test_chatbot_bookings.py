"""챗봇 "내 예약" 어댑터 (`modules/chatbot/bookings.py`) — booking.service 결과를 챗봇 도구 모양으로."""

import uuid

import pytest
from ai.agent.tools.booking_store import BookingError
from sqlalchemy.orm import Session

from modules.chatbot.bookings import BookingGateway
from test_booking_patient import make_hospital, patient, post, slot, staff


@pytest.fixture
def db(db_engine):
    with Session(db_engine, expire_on_commit=False) as s:
        yield s


def me(client, headers) -> str:
    return client.get("/api/v1/me", headers=headers).json()["id"]


def test_list_and_get_my_bookings_in_chat_tool_shape(client, db):
    h = make_hospital(db)
    h.name_en = "Example Dermatology Clinic"
    db.commit()
    p = patient(client)
    r = post(client, h, p, preferred_slots=[slot(3)])
    assert r.status_code == 201, r.json()
    req_id = r.json()["id"]

    gw = BookingGateway(db)
    rows = gw.list_for_patient(me(client, p))
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == req_id and row["hospital_id"] == h.id
    assert row["hospital_name_en"] == "Example Dermatology Clinic"
    assert row["status"] == "pending" and row["visited"] is False
    assert len(row["preferred"]) == 1 and len(row["preferred"][0]) == len("2026-11-20 10:00")  # 한국 시간 문자열
    assert row["confirmed_slot"] is None and row["proposed_slot"] is None
    assert "message" not in row and "health_info" not in row  # 요청서 원문은 모델에 안 보냄

    assert gw.get_for_patient(me(client, p), req_id)["id"] == req_id
    assert gw.list_for_patient(me(client, p), "confirmed") == []


def test_confirmed_and_proposed_slots(client, db):
    h = make_hospital(db)
    p = patient(client)
    s = staff(db, h)
    req_id = post(client, h, p, preferred_slots=[slot(3)]).json()["id"]
    when = slot(5)
    r = client.post(f"/api/v1/tenant/booking-requests/{req_id}/propose", json={"slot": when}, headers=s)
    assert r.status_code == 200, r.json()

    row = BookingGateway(db).list_for_patient(me(client, p))[0]
    assert row["status"] == "proposed"
    assert row["proposed_slot"] is not None and row["confirmed_slot"] is None


def test_other_patient_and_bad_ids(client, db):
    h = make_hospital(db)
    a = patient(client, "a@example.com")
    b = patient(client, "b@example.com")
    req_id = post(client, h, a).json()["id"]
    gw = BookingGateway(db)

    assert gw.list_for_patient(me(client, b)) == []
    with pytest.raises(BookingError):
        gw.get_for_patient(me(client, b), req_id)  # 남의 요청은 없는 것과 같음
    with pytest.raises(BookingError):
        gw.get_for_patient(me(client, a), str(uuid.uuid4()))
    assert gw.list_for_patient("demo-patient-1") == []  # UUID가 아닌 id


def test_aftercare_for_chat_card(db):
    """챗봇 사후관리 카드: 방문 완료 + 사후관리 지원 병원만 열 수 있음, 이미 있는 대화 id, 메시지는 보내지 않음."""
    from modules.aftercare import service as aftercare
    from modules.aftercare.models import AftercareMessage
    from test_aftercare_tenant import _patient, _req, _tenant

    p, t = _patient(db), _tenant(db)
    gw = BookingGateway(db)
    before = _req(db, p, t, visited=False)
    assert gw.aftercare_for(str(p.id), str(before.id)) == {"available": False}
    r = _req(db, p, _tenant(db, 9002))
    assert gw.aftercare_for(str(p.id), str(r.id)) == {"available": True, "thread_id": None}
    assert db.query(AftercareMessage).count() == 0  # 열기만, 보내지 않음
    thread = aftercare.patient_open(db, p.id, r.id, "receipt please")
    assert gw.aftercare_for(str(p.id), str(r.id)) == {"available": True, "thread_id": str(thread.id)}
    assert gw.aftercare_for(str(_patient(db).id), str(r.id)) == {"available": False}  # 남의 예약
    off = _req(db, p, _tenant(db, 9003, aftercare_on=False))
    assert gw.aftercare_for(str(p.id), str(off.id)) == {"available": False}
    assert gw.aftercare_for("x", "y") == {"available": False}


def test_aftercare_tool_uses_gateway(db):
    from ai.agent.tools.chat_tools import build_registry
    from ai.agent.tools.registry import ToolContext
    from test_aftercare_tenant import _patient, _req, _tenant

    p, t = _patient(db), _tenant(db)
    r = _req(db, p, t)
    ctx = ToolContext(patient_id=str(p.id), store=BookingGateway(db))
    out = build_registry().run("open_aftercare_thread", {"booking_id": str(r.id), "topic": "documents", "message": "Need receipt"}, ctx)
    assert out["status"] == "opened" and out["booking_id"] == str(r.id) and out["thread_id"] == ""
    assert "Not sent yet" in out["note"]
    off = _req(db, p, _tenant(db, 9002, aftercare_on=False))
    out = build_registry().run("open_aftercare_thread", {"booking_id": str(off.id), "topic": "documents", "message": "x"}, ctx)
    assert out["status"] == "not_available" and "directly" in out["reason"]
