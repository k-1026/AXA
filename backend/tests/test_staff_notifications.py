"""병원(직원) 알림 (11/27): 환자가 요청·취소·수락·질문하면 그 병원에 한 줄 → 대시보드가 Realtime으로 바로 다시 불러옴. 가상 데이터만."""

import jwt
import pytest
from sqlalchemy.orm import Session

from core.config import get_settings
from modules.notification.models import StaffNotification
from modules.tenant.models import Tenant

from test_booking_patient import patient, post, make_hospital, slot, staff


@pytest.fixture
def db(db_engine):
    with Session(db_engine, expire_on_commit=False) as s:
        yield s


def _rows(db, h):
    db.expire_all()
    t = db.query(Tenant).filter_by(hospital_id=h.id).one()
    return [(n.kind, n.status) for n in db.query(StaffNotification).filter_by(tenant_id=t.id).order_by(StaffNotification.id)]


def test_환자가_요청_질문_취소하면_그_병원에만_알림(client, db):
    h, other, me = make_hospital(db), make_hospital(db), patient(client)
    rid = post(client, h, me).json()["id"]
    assert _rows(db, h) == [("request", None)]

    r = client.post(f"/api/v1/me/booking-requests/{rid}/questions", json={"text": "What should I bring?"}, headers=me)
    assert r.status_code == 201, r.json()
    assert client.post(f"/api/v1/me/booking-requests/{rid}/cancel", json={}, headers=me).status_code == 200
    assert _rows(db, h) == [("request", None), ("question", None), ("status", "cancelled")]
    assert _rows(db, other) == []  # 다른 병원에는 없음


def test_병원이_바꾼_것은_병원_알림_없음_환자가_수락하면_있음(client, db):
    h, me = make_hospital(db), patient(client)
    sh = staff(db, h)
    rid = post(client, h, me).json()["id"]
    assert client.post(f"/api/v1/tenant/booking-requests/{rid}/propose", json={"slot": slot(4)}, headers=sh).status_code == 200
    assert _rows(db, h) == [("request", None)]  # 자기가 한 일은 알리지 않음
    assert client.post(f"/api/v1/me/booking-requests/{rid}/accept", headers=me).status_code == 200
    assert _rows(db, h) == [("request", None), ("status", "confirmed")]


def test_직원_realtime_토큰에는_자기_병원_tenant_id(client, db, monkeypatch):
    h = make_hospital(db)
    sh = staff(db, h)
    r = client.post("/api/v1/tenant/notifications/realtime-token", headers=sh)
    assert (r.status_code, r.json()["code"]) == (503, "realtime.unavailable")  # 설정 없음

    s = get_settings()
    monkeypatch.setattr(s, "supabase_url", "https://proj.supabase.example")
    monkeypatch.setattr(s, "supabase_jwt_secret", "test-supabase-jwt-secret-0123456789abcdef")
    r = client.post("/api/v1/tenant/notifications/realtime-token", headers=sh)
    assert r.status_code == 200, r.json()
    claims = jwt.decode(r.json()["token"], "test-supabase-jwt-secret-0123456789abcdef", algorithms=["HS256"], audience="authenticated")
    t = db.query(Tenant).filter_by(hospital_id=h.id).one()
    assert claims["tenant_id"] == str(t.id) and claims["role"] == "authenticated"

    me = patient(client)  # 환자 토큰으로는 못 받음
    assert client.post("/api/v1/tenant/notifications/realtime-token", headers=me).status_code in (401, 403)
