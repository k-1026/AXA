"""B: 병원 계정(/tenant/me) · 사후관리 대화와 병원 계정 연동 · 대시보드 확정. 가상 데이터만."""

import itertools
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from core.security import create_access_token
from db_rows import demo_hospital, demo_staff
from modules.aftercare import service as aftercare
from modules.booking import service as booking
from modules.patient.models import Patient
from modules.tenant.models import Tenant

NOW = datetime(2026, 11, 16, 3, 0, tzinfo=timezone.utc)
SLOT = "2026-11-21T01:00:00+00:00"


@pytest.fixture
def db(db_engine):
    with Session(db_engine, expire_on_commit=False) as s:
        yield s


def _patient(db):
    p = Patient(email=f"d-{uuid.uuid4().hex[:8]}@example.test", password_hash="x", age14_confirmed_at=NOW)
    db.add(p)
    db.commit()
    return p


def _tenant(db, hid=9001, aftercare_on=True):
    demo_hospital(db, hid)  # hospital_id FK (0007)
    t = Tenant(hospital_id=hid, display_name=f"가상 병원 {hid}", requests_enabled=True, aftercare_enabled=aftercare_on)
    db.add(t)
    db.commit()
    return t


_slot_day = itertools.count()


def _next_slot() -> str:
    d = datetime.fromisoformat(SLOT.replace("Z", "+00:00")) + timedelta(days=next(_slot_day))
    return d.isoformat().replace("+00:00", "Z")


def _req(db, p, t, visited=True):
    when = _next_slot()
    r = booking.create_request(
        db, p.id, t.id,
        # 요청서마다 다른 날 (같은 환자 예약은 1시간 이내로 겹칠 수 없음, booking.time_conflict)
        dict(lang="zh-TW", nationality="TW", contact_method="email", preferred_slots=[when],
             department_code="dermatology", treatment="laser_toning", visa_needed=False),
    )
    if visited:
        booking.staff_act(db, t.id, "s", r.id, "confirm", datetime.fromisoformat(when.replace("Z", "+00:00")))
        booking.staff_act(db, t.id, "s", r.id, "visited")
    return r


def _h(t, staff_id=None):
    tok = create_access_token(staff_id or str(uuid.uuid4()), "staff", tenant_id=str(t.id))
    return {"Authorization": f"Bearer {tok}"}


# ---------- 병원 계정 ----------


def test_tenant_me_and_toggle_aftercare(client, db):
    t = _tenant(db, aftercare_on=False)
    r = client.get("/api/v1/tenant/me", headers=_h(t))
    assert r.status_code == 200 and r.json()["aftercare_enabled"] is False
    r = client.patch("/api/v1/tenant/me", json={"aftercare_enabled": True}, headers=_h(t))
    assert r.json()["aftercare_enabled"] is True
    db.refresh(t)
    assert t.aftercare_enabled is True


# ---------- 사후관리 열기 규칙 ----------


def test_patient_open_requires_visited(db):
    p, t = _patient(db), _tenant(db)
    r = _req(db, p, t, visited=False)
    with pytest.raises(Exception) as e:
        aftercare.patient_open(db, p.id, r.id, "붉은기가 있어요")
    assert e.value.code == "booking.invalid_transition"


def test_patient_open_blocked_when_hospital_disabled(db):
    p, t = _patient(db), _tenant(db, aftercare_on=False)
    r = _req(db, p, t)
    with pytest.raises(Exception) as e:
        aftercare.patient_open(db, p.id, r.id, "질문")
    assert e.value.code == "booking.invalid_transition"


def test_other_patient_cannot_open(db):
    p, other, t = _patient(db), _patient(db), _tenant(db)
    r = _req(db, p, t)
    with pytest.raises(Exception) as e:
        aftercare.patient_open(db, other.id, r.id, "질문")
    assert e.value.code == "not_found"


# ---------- 병원용 API (연동·격리) ----------


def test_thread_flow_list_reply_resolve(client, db):
    p, t = _patient(db), _tenant(db)
    staff = demo_staff(db, t.id)  # 답장의 staff_id FK → 실제 직원 행 (0007)
    r = _req(db, p, t)
    thread = aftercare.patient_open(db, p.id, r.id, "做完第三天了，臉還是有點紅", photo=True)

    lst = client.get("/api/v1/tenant/aftercare", headers=_h(t, str(staff.id))).json()
    assert len(lst) == 1 and lst[0]["status"] == "new" and lst[0]["unanswered"] == 1
    assert lst[0]["lang"] == "zh-TW"

    out = client.post(f"/api/v1/tenant/aftercare/{thread.id}/messages", json={"text": "사진 확인했어요"}, headers=_h(t, str(staff.id))).json()
    assert out["status"] == "in_progress"
    assert [m["sender"] for m in out["messages"]] == ["patient", "staff"]
    assert out["messages"][0]["has_photo"] is True
    assert client.get("/api/v1/tenant/aftercare", headers=_h(t)).json()[0]["unanswered"] == 0

    out = client.patch(f"/api/v1/tenant/aftercare/{thread.id}", json={"status": "resolved", "tags": ["붉은기"]}, headers=_h(t)).json()
    assert out["status"] == "resolved" and out["tags"] == ["붉은기"]


def test_other_hospital_cannot_see_thread(client, db):
    p, a, b = _patient(db), _tenant(db, 9001), _tenant(db, 9002)
    thread = aftercare.patient_open(db, p.id, _req(db, p, a).id, "질문")
    assert client.get("/api/v1/tenant/aftercare", headers=_h(b)).json() == []
    assert client.get(f"/api/v1/tenant/aftercare/{thread.id}", headers=_h(b)).status_code == 404
    assert client.post(f"/api/v1/tenant/aftercare/{thread.id}/messages", json={"text": "x"}, headers=_h(b)).status_code == 404


def test_empty_reply_is_422(client, db):
    p, t = _patient(db), _tenant(db)
    thread = aftercare.patient_open(db, p.id, _req(db, p, t).id, "질문")
    r = client.post(f"/api/v1/tenant/aftercare/{thread.id}/messages", json={"text": "  "}, headers=_h(t))
    assert r.status_code == 422 and r.json()["code"] == "validation"


def test_patient_token_cannot_use_aftercare_api(client, db):
    tok = create_access_token(str(uuid.uuid4()), "patient", session_id="s")
    r = client.get("/api/v1/tenant/aftercare", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403


# ---------- 대시보드 확정 버튼 ----------


def test_dashboard_confirm_with_first_preferred_slot(client, db):
    """대시보드 '예약 확정' = 첫 희망 시간으로 confirm → 목록에서 상태가 바뀜"""
    p, t = _patient(db), _tenant(db)
    r = _req(db, p, t, visited=False)
    lst = client.get("/api/v1/tenant/booking-requests?status=pending", headers=_h(t)).json()
    slot = lst[0]["preferred_slots"][0]
    out = client.post(f"/api/v1/tenant/booking-requests/{r.id}/confirm", json={"slot": slot}, headers=_h(t)).json()
    assert out["status"] == "confirmed" and out["confirmed_slot"].startswith(slot[:16])
    assert client.get("/api/v1/tenant/booking-requests?status=pending", headers=_h(t)).json() == []
