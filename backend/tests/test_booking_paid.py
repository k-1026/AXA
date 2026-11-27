"""결제 확인(paid): 방문 완료 → 병원이 결제 금액·수단 입력 (11/27, 0018)"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import AppError
from core.security import create_access_token
from modules.booking import service
from modules.booking.models import BookingEvent
from modules.notification.models import Notification
from test_booking_tenant import _data, _patient, _tenant

SLOT = datetime(2026, 11, 16, 2, 0, tzinfo=timezone.utc)


@pytest.fixture
def db(db_engine):
    with Session(db_engine, expire_on_commit=False) as s:
        yield s


def _visited(db):
    t = _tenant(db)
    r = service.create_request(db, _patient(db).id, t.id, _data())
    service.staff_act(db, t.id, "s", r.id, "confirm", SLOT)
    service.staff_act(db, t.id, "s", r.id, "visited")
    return t, r


def test_paid_after_visited_saves_amount_and_notifies(db):
    t, r = _visited(db)
    out = service.staff_act(db, t.id, "s", r.id, "paid", amount=730000, method="card")
    assert (out.status, out.paid_amount, out.paid_method) == ("paid", 730000, "card")
    assert db.scalar(select(BookingEvent.to_status).where(BookingEvent.request_id == r.id).order_by(BookingEvent.id.desc())) == "paid"
    assert db.scalar(select(Notification.status).where(Notification.request_id == r.id).order_by(Notification.id.desc())) == "paid"


def test_paid_only_from_visited(db):
    t = _tenant(db)
    r = service.create_request(db, _patient(db).id, t.id, _data())
    with pytest.raises(AppError) as e:
        service.staff_act(db, t.id, "s", r.id, "paid", amount=1000, method="cash")
    assert e.value.code == "booking.invalid_transition"


@pytest.mark.parametrize("amount,method", [(None, "card"), (0, "card"), (-5, "card"), (1000, None), (1000, "bitcoin")])
def test_paid_needs_amount_and_method(db, amount, method):
    t, r = _visited(db)
    with pytest.raises(AppError) as e:
        service.staff_act(db, t.id, "s", r.id, "paid", amount=amount, method=method)
    assert e.value.status_code == 422


def test_amount_only_for_paid(db):
    t = _tenant(db)
    r = service.create_request(db, _patient(db).id, t.id, _data())
    with pytest.raises(AppError) as e:
        service.staff_act(db, t.id, "s", r.id, "confirm", SLOT, amount=1000)
    assert e.value.status_code == 422


def test_paid_api(client, db):
    t, r = _visited(db)
    h = {"Authorization": "Bearer " + create_access_token(str(uuid.uuid4()), "staff", tenant_id=str(t.id))}
    res = client.post(f"/api/v1/tenant/booking-requests/{r.id}/paid", json={"amount": 1200000, "method": "transfer"}, headers=h)
    assert res.status_code == 200
    assert (res.json()["status"], res.json()["paid_amount"], res.json()["paid_method"]) == ("paid", 1200000, "transfer")
    lst = client.get("/api/v1/tenant/booking-requests?status=paid", headers=h).json()
    assert [x["id"] for x in lst] == [str(r.id)]
