"""B: 예약 상태 흐름 · 병원용 API · 대시보드 summary. 가상 데이터만."""

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from core.security import create_access_token
from db_rows import demo_hospital
from modules.booking import analytics, service
from modules.booking.models import BookingEvent, BookingRequest
from modules.patient.models import Patient
from modules.tenant.models import Tenant

NOW = datetime(2026, 11, 16, 3, 0, tzinfo=timezone.utc)  # 한국 11/16 12:00


def _patient(db: Session) -> Patient:
    p = Patient(
        email=f"demo-{uuid.uuid4().hex[:8]}@example.test",
        password_hash="x",
        age14_confirmed_at=NOW,
    )
    db.add(p)
    db.commit()
    return p


def _tenant(db: Session, name: str = "예시 피부과의원", hospital_id: int = 9001, enabled: bool = True) -> Tenant:
    demo_hospital(db, hospital_id)  # hospital_id FK (0007)
    t = Tenant(hospital_id=hospital_id, display_name=name, requests_enabled=enabled, registration_no="DEMO-0001")
    db.add(t)
    db.commit()
    return t


def _data(**kw) -> dict:
    base = dict(
        lang="zh-TW",
        nationality="TW",
        contact_method="email",
        preferred_slots=["2026-11-21T01:00:00Z"],
        department_code="dermatology",
        treatment="laser_toning",
        visa_needed=False,
        message_original="想做雷射淨膚",
        patient_timezone="Asia/Taipei",
    )
    base.update(kw)
    return base


def _staff_headers(tenant: Tenant) -> dict:
    token = create_access_token(str(uuid.uuid4()), "staff", tenant_id=str(tenant.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def db(db_engine):
    with Session(db_engine, expire_on_commit=False) as s:
        yield s


# ---------- 상태 흐름 ----------


def test_create_starts_pending_and_logs_event(db):
    p, t = _patient(db), _tenant(db)
    req = service.create_request(db, p.id, t.id, _data())
    assert req.status == "pending"
    events = db.query(BookingEvent).filter_by(request_id=req.id).all()
    assert [(e.from_status, e.to_status) for e in events] == [(None, "pending")]


def test_not_enabled_tenant_rejects_requests(db):
    p, t = _patient(db), _tenant(db, enabled=False)
    with pytest.raises(Exception) as e:
        service.create_request(db, p.id, t.id, _data())
    assert e.value.code == "not_found"


def test_same_hospital_same_day_is_409(db):
    p, t = _patient(db), _tenant(db)
    service.create_request(db, p.id, t.id, _data())
    with pytest.raises(Exception) as e:
        service.create_request(db, p.id, t.id, _data(preferred_slots=["2026-11-21T05:00:00Z"]))
    assert e.value.code == "booking.same_day"


def test_staff_cannot_confirm_time_overlapping_patients_other_confirmed_booking(db):
    """병원이 확정·제안하려는 시간이 그 환자의 다른 병원 확정 예약과 1시간 이내면 409 booking.patient_conflict."""
    p, t1, t2 = _patient(db), _tenant(db), _tenant(db, "예시 안과의원", 9002)
    a = service.create_request(db, p.id, t1.id, _data(preferred_slots=["2026-11-21T01:00:00Z"]))
    b = service.create_request(db, p.id, t2.id, _data(preferred_slots=["2026-11-21T03:00:00Z"]))
    service.staff_act(db, t1.id, "s", a.id, "confirm", datetime(2026, 11, 21, 1, 0, tzinfo=timezone.utc))
    with pytest.raises(Exception) as e:
        service.staff_act(db, t2.id, "s", b.id, "propose", datetime(2026, 11, 21, 1, 30, tzinfo=timezone.utc))
    assert e.value.code == "booking.patient_conflict"
    ok = service.staff_act(db, t2.id, "s", b.id, "confirm", datetime(2026, 11, 21, 3, 0, tzinfo=timezone.utc))
    assert ok.status == "confirmed"


def test_full_flow_each_change_logs_one_event(db):
    p, t = _patient(db), _tenant(db)
    req = service.create_request(db, p.id, t.id, _data())
    slot = datetime(2026, 11, 21, 1, 0, tzinfo=timezone.utc)
    service.staff_act(db, t.id, "staff-1", req.id, "propose", slot)
    service.patient_accept(db, p.id, req.id)
    req = service.staff_act(db, t.id, "staff-1", req.id, "visited")
    assert req.status == "visited"
    events = db.query(BookingEvent).filter_by(request_id=req.id).order_by(BookingEvent.id).all()
    assert [e.to_status for e in events] == ["pending", "proposed", "confirmed", "visited"]


def test_invalid_transition_is_409(db):
    p, t = _patient(db), _tenant(db)
    req = service.create_request(db, p.id, t.id, _data())
    with pytest.raises(Exception) as e:
        service.staff_act(db, t.id, "staff-1", req.id, "visited")  # pending → visited X
    assert e.value.code == "booking.invalid_transition"


def test_patient_cannot_cancel_confirmed(db):
    p, t = _patient(db), _tenant(db)
    req = service.create_request(db, p.id, t.id, _data())
    service.staff_act(db, t.id, "s", req.id, "confirm", NOW)
    with pytest.raises(Exception) as e:
        service.patient_cancel(db, p.id, req.id, "schedule")
    assert e.value.code == "booking.invalid_transition"


def test_other_patient_gets_404(db):
    p, other, t = _patient(db), _patient(db), _tenant(db)
    req = service.create_request(db, p.id, t.id, _data())
    with pytest.raises(Exception) as e:
        service.get_for_patient(db, other.id, req.id)
    assert e.value.code == "not_found"


# ---------- 병원용 API (권한·격리) ----------


def test_patient_token_cannot_use_tenant_api(client, db):
    token = create_access_token(str(uuid.uuid4()), "patient", session_id="s")
    r = client.get("/api/v1/tenant/booking-requests", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403 and r.json()["code"] == "auth.forbidden"


def test_staff_of_other_hospital_gets_404(client, db):
    p, a, b = _patient(db), _tenant(db, "A", 9001), _tenant(db, "B", 9002)
    req = service.create_request(db, p.id, a.id, _data())
    r = client.get(f"/api/v1/tenant/booking-requests/{req.id}", headers=_staff_headers(b))
    assert r.status_code == 404 and r.json()["code"] == "not_found"
    r = client.get("/api/v1/tenant/booking-requests", headers=_staff_headers(b))
    assert r.json() == []


def test_staff_confirm_via_api(client, db):
    p, t = _patient(db), _tenant(db)
    req = service.create_request(db, p.id, t.id, _data())
    r = client.post(
        f"/api/v1/tenant/booking-requests/{req.id}/confirm",
        json={"slot": "2026-11-21T01:00:00Z"},
        headers=_staff_headers(t),
    )
    assert r.status_code == 200 and r.json()["status"] == "confirmed"
    r = client.post(f"/api/v1/tenant/booking-requests/{req.id}/no-show", headers=_staff_headers(t))
    assert r.json()["status"] == "no_show"


def test_confirm_without_slot_is_422(client, db):
    p, t = _patient(db), _tenant(db)
    req = service.create_request(db, p.id, t.id, _data())
    r = client.post(f"/api/v1/tenant/booking-requests/{req.id}/confirm", headers=_staff_headers(t))
    assert r.status_code == 422 and r.json()["code"] == "validation"


def test_거절_사유는_이력에_코드로_남는다(client, db):
    p, t = _patient(db), _tenant(db)
    req = service.create_request(db, p.id, t.id, _data())
    r = client.post(f"/api/v1/tenant/booking-requests/{req.id}/reject", json={"reason": "fully_booked"},
                    headers=_staff_headers(t))
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    ev = db.query(BookingEvent).filter_by(request_id=req.id, to_status="rejected").one()
    assert ev.reason == "fully_booked" and ev.actor_type == "staff"


def test_거절_사유는_선택(client, db):
    p, t = _patient(db), _tenant(db)
    req = service.create_request(db, p.id, t.id, _data())
    r = client.post(f"/api/v1/tenant/booking-requests/{req.id}/reject", headers=_staff_headers(t))
    assert r.status_code == 200
    assert db.query(BookingEvent).filter_by(request_id=req.id, to_status="rejected").one().reason is None


def test_목록에_없는_거절_사유_또는_거절이_아닌_행동의_사유는_422(client, db):
    p, t = _patient(db), _tenant(db)
    req = service.create_request(db, p.id, t.id, _data())
    bad = client.post(f"/api/v1/tenant/booking-requests/{req.id}/reject", json={"reason": "아무 말"},
                      headers=_staff_headers(t))
    assert bad.status_code == 422 and bad.json()["code"] == "validation"
    wrong = client.post(f"/api/v1/tenant/booking-requests/{req.id}/confirm",
                        json={"slot": "2026-11-21T01:00:00Z", "reason": "other"}, headers=_staff_headers(t))
    assert wrong.status_code == 422 and wrong.json()["code"] == "validation"
    db.refresh(req)
    assert req.status == "pending"  # 둘 다 아무것도 바뀌지 않음


# ---------- 대시보드 summary ----------


def _at(db, req_id, when):
    """테스트용: 요청·이벤트 시각을 과거로 옮김"""
    db.query(BookingRequest).filter_by(id=req_id).update({"created_at": when})
    db.query(BookingEvent).filter_by(request_id=req_id).update({"created_at": when})
    db.commit()


def test_summary_counts_only_my_tenant_and_period(db):
    t, other = _tenant(db, "A", 9001), _tenant(db, "B", 9002)
    slot = datetime(2026, 11, 16, 2, 0, tzinfo=timezone.utc)  # 한국 11/16 11:00
    # 이번 기간(11/1~11/16): 요청 3, 확정 2, 방문 1, 취소 1
    reqs = []
    for i in range(3):
        reqs.append(service.create_request(db, _patient(db).id, t.id, _data()))
    service.staff_act(db, t.id, "s", reqs[0].id, "confirm", slot)
    service.staff_act(db, t.id, "s", reqs[0].id, "visited")
    service.staff_act(db, t.id, "s", reqs[1].id, "confirm", slot)
    service.patient_cancel(db, reqs[2].patient_id, reqs[2].id, "cost")
    for r in reqs:
        _at(db, r.id, datetime(2026, 11, 10, tzinfo=timezone.utc))
    # 지난 기간(10/16~10/31): 요청 1
    old = service.create_request(db, _patient(db).id, t.id, _data())
    _at(db, old.id, datetime(2026, 10, 20, tzinfo=timezone.utc))
    # 다른 병원 요청은 세지 않음
    service.create_request(db, _patient(db).id, other.id, _data())

    s = analytics.summary(db, t.id, date(2026, 11, 1), date(2026, 11, 16), today=date(2026, 11, 16))
    k = {x["key"]: x for x in s["kpi"]}
    assert (k["requests"]["now"], k["requests"]["prev"]) == (3, 1)
    assert k["confirmed"]["now"] == 2 and k["visited"]["now"] == 1
    assert k["cancelRate"]["now"] == 50
    assert k["views"]["now"] is None and "views" in s["suppressed"]
    assert s["period"]["prevFrom"] == "2026-10-16" and s["period"]["prevTo"] == "2026-10-31"
    assert s["today"]["visitsToday"] == 1  # reqs[1] 확정, 오늘 11:00
    assert s["today"]["newRequests"] == 1  # 지난 기간 요청 1건이 아직 pending


def test_summary_api_requires_staff_and_returns_shape(client, db):
    t = _tenant(db)
    r = client.get("/api/v1/tenant/analytics/summary?from=2026-11-01&to=2026-11-16", headers=_staff_headers(t))
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"period", "kpi", "funnel", "today", "suppressed"}
    assert [x["key"] for x in body["kpi"]] == ["views", "requests", "confirmed", "visited", "cancelRate"]
    assert client.get("/api/v1/tenant/analytics/summary").status_code == 401
    bad = client.get("/api/v1/tenant/analytics/summary?from=2026-11-20&to=2026-11-01", headers=_staff_headers(t))
    assert bad.status_code == 422


def _hours(db: Session, hospital_id: int) -> None:
    """월~금 10:00~18:00 (점심 13~14), 토·일 휴진."""
    from datetime import time

    from modules.hospital.models import HospitalHours
    for i, day in enumerate(("mon", "tue", "wed", "thu", "fri", "sat", "sun")):
        open_ = i < 5
        db.add(HospitalHours(hospital_id=hospital_id, day=day, day_order=i, state="open" if open_ else "closed",
                             open_time=time(10) if open_ else None, close_time=time(18) if open_ else None,
                             lunch_start=time(13) if open_ else None, lunch_end=time(14) if open_ else None,
                             source="test", checked_at=NOW))
    db.commit()


def test_hospital_cannot_confirm_its_own_proposal_patient_accepts(db):
    # 확정은 양쪽이 동의한 시간만: 환자가 고른 시간(pending)은 병원이 확정, 병원이 제안한 시간은 환자가 수락 (11/24 사용자 결정)
    p, t = _patient(db), _tenant(db)
    req = service.create_request(db, p.id, t.id, _data())
    service.staff_act(db, t.id, "staff-1", req.id, "propose", datetime(2026, 11, 20, 1, 0, tzinfo=timezone.utc))
    with pytest.raises(Exception) as e:
        service.staff_act(db, t.id, "staff-1", req.id, "confirm")
    assert e.value.code == "booking.invalid_transition"
    assert service.patient_accept(db, p.id, req.id).status == "confirmed"


@pytest.mark.parametrize("kst_slot,ok", [
    ((2026, 11, 20, 11, 0), True),    # 금 11:00
    ((2026, 11, 21, 11, 0), False),   # 토 — 휴진
    ((2026, 11, 22, 11, 0), False),   # 일 — 휴진
    ((2026, 11, 20, 9, 0), False),    # 금 09:00 — 진료 전
    ((2026, 11, 20, 18, 0), False),   # 금 18:00 — 진료 끝 (끝 시각은 X)
    ((2026, 11, 20, 13, 30), False),  # 점심
])
def test_proposal_must_be_within_hospital_hours(db, kst_slot, ok):
    from zoneinfo import ZoneInfo
    p, t = _patient(db), _tenant(db)
    _hours(db, t.hospital_id)
    req = service.create_request(db, p.id, t.id, _data())
    at = datetime(*kst_slot, tzinfo=ZoneInfo("Asia/Seoul"))
    if ok:
        assert service.staff_act(db, t.id, "staff-1", req.id, "propose", at).status == "proposed"
    else:
        with pytest.raises(Exception) as e:
            service.staff_act(db, t.id, "staff-1", req.id, "propose", at)
        assert e.value.code == "validation" and e.value.detail["errors"][0]["loc"] == ["slot"]


def test_proposal_without_hours_data_is_not_blocked(db):
    p, t = _patient(db), _tenant(db)  # 진료시간 데이터가 없는 병원 → 막지 않음 (모르는 것을 휴진으로 보지 않음)
    req = service.create_request(db, p.id, t.id, _data())
    assert service.staff_act(db, t.id, "staff-1", req.id, "propose", datetime(2026, 11, 22, 2, 0, tzinfo=timezone.utc)).status == "proposed"
