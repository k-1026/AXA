"""방문 전 리마인드 알림 (notification/reminders.py, docs/booking-rules.md 3-2 N1)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.booking import service as booking
from modules.notification import reminders
from modules.notification.models import Notification
from test_booking_tenant import _data, _patient, _tenant
from test_maintenance import SECRET, bearer, cron_secret  # noqa: F401  (fixture)

VISIT = datetime(2026, 12, 4, 7, 0, tzinfo=timezone.utc)  # 한국 16:00


@pytest.fixture
def db(db_engine):
    with Session(db_engine, expire_on_commit=False) as s:
        yield s


def _confirmed(db, hospital_id=9001, when=VISIT):
    p, t = _patient(db), _tenant(db, hospital_id=hospital_id)
    r = booking.create_request(db, p.id, t.id, _data(preferred_slots=[when.isoformat().replace("+00:00", "Z")]))
    booking.staff_act(db, t.id, "s", r.id, "confirm", when)
    return p, t, r


def _sent(db, r):
    return list(db.scalars(select(Notification.status).where(Notification.request_id == r.id, Notification.kind == "reminder")))


def test_stage_for():
    assert reminders.stage_for(timedelta(hours=60)) is None
    assert reminders.stage_for(timedelta(hours=47)) == "48h"
    assert reminders.stage_for(timedelta(hours=24)) == "24h"
    assert reminders.stage_for(timedelta(hours=3)) == "24h"
    assert reminders.stage_for(timedelta(minutes=90)) == "2h"
    assert reminders.stage_for(timedelta(minutes=-1)) is None


def test_단계마다_한_번씩_보낸다(db):
    _, _, r = _confirmed(db)
    assert reminders.send_due(db, VISIT - timedelta(hours=50)) == 0  # 아직 이름
    assert reminders.send_due(db, VISIT - timedelta(hours=47)) == 1
    assert reminders.send_due(db, VISIT - timedelta(hours=46)) == 0  # 같은 단계 다시 X
    assert reminders.send_due(db, VISIT - timedelta(hours=23)) == 1
    assert reminders.send_due(db, VISIT - timedelta(hours=1)) == 1
    assert reminders.send_due(db, VISIT + timedelta(hours=1)) == 0  # 지난 예약
    assert sorted(_sent(db, r)) == ["24h", "2h", "48h"]


def test_늦게_돌면_지금_단계만_보내고_앞_단계는_몰아_보내지_않는다(db):
    _, _, r = _confirmed(db)
    assert reminders.send_due(db, VISIT - timedelta(hours=1)) == 1
    assert reminders.send_due(db, VISIT - timedelta(minutes=30)) == 0
    assert _sent(db, r) == ["2h"]


def test_확정이_아니면_보내지_않는다(db):
    p, t = _patient(db), _tenant(db)
    booking.create_request(db, p.id, t.id, _data(preferred_slots=["2026-12-04T07:00:00Z"]))  # 확인 대기
    _, _, r = _confirmed(db, 9002, VISIT + timedelta(days=1))
    booking.staff_act(db, r.tenant_id, "s", r.id, "no_show")  # 확정 → 노쇼
    assert reminders.send_due(db, VISIT - timedelta(hours=1)) == 0


def test_알림은_환자_알림_목록에_reminder로(db):
    p, _, r = _confirmed(db)
    reminders.send_due(db, VISIT - timedelta(hours=20))
    n = db.scalar(select(Notification).where(Notification.patient_id == p.id, Notification.kind == "reminder"))
    assert (n.status, n.request_id, n.read_at) == ("24h", r.id, None)


def test_정기_작업_주소는_cron_비밀값이_있어야(client, cron_secret):  # noqa: F811
    assert client.post("/api/v1/internal/reminders").status_code == 401
    r = client.post("/api/v1/internal/reminders", headers=bearer(SECRET))
    assert r.status_code == 200 and r.json() == {"reminders": 0}
