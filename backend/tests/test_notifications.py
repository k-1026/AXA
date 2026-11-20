"""A: 사이트 안 알림 (결정 27) — 병원이 상태를 바꾸거나 답장하면 환자에게 한 줄, 자기 알림만, Realtime 토큰. 가상 데이터만."""

import uuid

import jwt
import pytest
from sqlalchemy.orm import Session

from core.config import get_settings
from db_rows import demo_staff
from modules.notification.models import Notification

from test_booking_patient import SIGNUP, make_hospital, patient, post, slot, staff


@pytest.fixture
def db(db_engine):
    with Session(db_engine, expire_on_commit=False) as s:
        yield s


def _mine(client, me):
    r = client.get("/api/v1/me/notifications", headers=me)
    assert r.status_code == 200, r.json()
    return r.json()


def test_병원이_확정_답장하면_알림_환자가_취소하면_알림_없음(client, db):
    h, me = make_hospital(db), patient(client)
    sh = staff(db, h)
    rid = post(client, h, me).json()["id"]
    assert _mine(client, me) == []  # 요청만 한 상태

    assert client.post(f"/api/v1/tenant/booking-requests/{rid}/confirm", json={"slot": slot(3)}, headers=sh).status_code == 200
    assert client.post(f"/api/v1/tenant/booking-requests/{rid}/replies", json={"text": "확정했어요"}, headers=sh).status_code == 201
    got = _mine(client, me)
    assert [(n["kind"], n["status"]) for n in got] == [("reply", None), ("status", "confirmed")]
    assert all(n["request_id"] == rid and n["hospital_id"] == h.id and n["read"] is False for n in got)

    rid2 = post(client, make_hospital(db), me).json()["id"]
    assert client.post(f"/api/v1/me/booking-requests/{rid2}/cancel", json={}, headers=me).status_code == 200
    assert len(_mine(client, me)) == 2  # 내가 한 취소는 알리지 않음


def test_사후관리_답장도_알림(client, db):
    from modules.aftercare import service as aftercare
    from modules.patient.models import Patient
    from modules.tenant.models import Tenant

    h, me = make_hospital(db), patient(client)
    sh = staff(db, h)
    rid = post(client, h, me).json()["id"]
    client.post(f"/api/v1/tenant/booking-requests/{rid}/confirm", json={"slot": slot(3)}, headers=sh)
    client.post(f"/api/v1/tenant/booking-requests/{rid}/visited", json={}, headers=sh)
    t = db.query(Tenant).filter_by(hospital_id=h.id).one()
    t.aftercare_enabled = True
    db.commit()
    p = db.query(Patient).filter_by(email=SIGNUP["email"]).one()
    thread = aftercare.patient_open(db, p.id, uuid.UUID(rid), "receipt?")
    aftercare.tenant_reply(db, t.id, str(demo_staff(db, t.id).id), thread.id, "보내 드릴게요")
    kinds = [n["kind"] for n in _mine(client, me)]
    assert kinds[0] == "aftercare" and "status" in kinds


def test_읽음은_내_것만_모두_읽음도(client, db):
    h, me = make_hospital(db), patient(client)
    other = patient(client, "other-n@example.com")
    sh = staff(db, h)
    rid = post(client, h, me).json()["id"]
    client.post(f"/api/v1/tenant/booking-requests/{rid}/reject", json={"reason": "fully_booked"}, headers=sh)
    h2 = make_hospital(db)
    oid = post(client, h2, other).json()["id"]
    client.post(f"/api/v1/tenant/booking-requests/{oid}/reject", json={}, headers=staff(db, h2))
    mine = _mine(client, me)
    assert len(mine) == 1 and mine[0]["status"] == "rejected"
    theirs = db.query(Notification).filter(Notification.id != mine[0]["id"]).all()

    r = client.post("/api/v1/me/notifications/read", json={"ids": [mine[0]["id"]] + [n.id for n in theirs]}, headers=me)
    assert r.json() == {"updated": 1}  # 남의 알림 id는 무시
    assert _mine(client, me)[0]["read"] is True
    assert all(n.read_at is None for n in db.query(Notification).filter(Notification.id != mine[0]["id"]))
    assert client.post("/api/v1/me/notifications/read", json={}, headers=other).json()["updated"] == len(theirs)


def test_다른_환자_알림은_안_보이고_직원_토큰은_403(client, db):
    h, me = make_hospital(db), patient(client)
    other = patient(client, "other2-n@example.com")
    rid = post(client, h, me).json()["id"]
    client.post(f"/api/v1/tenant/booking-requests/{rid}/reject", json={}, headers=staff(db, h))
    assert len(_mine(client, me)) == 1 and _mine(client, other) == []
    assert client.get("/api/v1/me/notifications", headers=staff(db, h)).status_code == 403
    assert client.get("/api/v1/me/notifications").status_code == 401


def test_탈퇴하면_알림도_삭제(client, db):
    h, me = make_hospital(db), patient(client)
    rid = post(client, h, me).json()["id"]
    client.post(f"/api/v1/tenant/booking-requests/{rid}/reject", json={}, headers=staff(db, h))
    assert db.query(Notification).count() == 1
    assert client.request("DELETE", "/api/v1/me", headers=me, json={"password": SIGNUP["password"]}).status_code == 204
    db.expire_all()
    assert db.query(Notification).count() == 0


def test_realtime_토큰(client, monkeypatch):
    me = patient(client)
    r = client.post("/api/v1/me/notifications/realtime-token", headers=me)
    assert (r.status_code, r.json()["code"]) == (503, "realtime.unavailable")  # 설정 없음

    s = get_settings()
    monkeypatch.setattr(s, "supabase_url", "https://proj.supabase.example")
    monkeypatch.setattr(s, "supabase_jwt_secret", "test-supabase-jwt-secret-0123456789abcdef")
    r = client.post("/api/v1/me/notifications/realtime-token", headers=me)
    assert r.status_code == 200, r.json()
    d = r.json()
    claims = jwt.decode(d["token"], "test-supabase-jwt-secret-0123456789abcdef", algorithms=["HS256"], audience="authenticated")
    me_id = client.get("/api/v1/me", headers=me).json()["id"]
    assert claims["sub"] == me_id and claims["role"] == "authenticated"
    assert d["url"] == "https://proj.supabase.example"
