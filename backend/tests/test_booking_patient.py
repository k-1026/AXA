"""A: 환자 예약 요청 · 내 예약 (router_patient). 가상 데이터만 (example.com, 가상 병원).

흐름: 환자 예약 요청(pending) → 병원 확정(B) → 환자 "내 예약"에 confirmed
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from core.db import utcnow
from core.security import create_access_token
from modules.consent.models import Consent
from modules.hospital.models import Hospital
from modules.tenant.models import Tenant

SIGNUP = {
    "email": "booker@example.com",
    "password": "test-password-1234",
    "age14_confirmed": True,
    "preferred_lang": "zh-TW",
    "timezone": "Asia/Taipei",
    "consents": [{"kind": "terms", "version": "2026-11-03"}, {"kind": "privacy", "version": "2026-11-03"}],
    "residency": {"country": "TW", "alien_registration": False, "domestic_residence": False, "health_insurance": False},
}


def slot(days: int = 3) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(minute=0, second=0, microsecond=0).isoformat()


def body(**kw) -> dict:
    b = {
        "department_code": "dermatology",
        "preferred_slots": [slot(3)],
        "patient_timezone": "Asia/Taipei",
        "lang": "zh-TW",
        "nationality": "TW",
        "contact_method": "email",
        "visa_needed": False,
        "residency": "short_term",
        "consents": [{"kind": "privacy", "version": "2026-11-03"}],
    }
    b.update(kw)
    return b


@pytest.fixture
def db(db_engine):
    with Session(db_engine, expire_on_commit=False) as s:
        yield s


def make_hospital(db, *, registered=True, verdict="normal", tenant=True, enabled=True) -> Hospital:
    h = Hospital(
        ykiho=f"Y-{uuid.uuid4().hex[:8]}", name_ko="예시피부과의원", is_registered_facility=registered,
        status_verdict=verdict, is_demo=True, source="테스트", fetched_at=utcnow(),
    )
    db.add(h)
    db.commit()
    if tenant:
        db.add(Tenant(hospital_id=h.id, display_name="예시피부과의원", requests_enabled=enabled, registration_no="DEMO-1"))
        db.commit()
    return h


def patient(client, email="booker@example.com") -> dict:
    r = client.post("/api/v1/auth/patient/signup", json={**SIGNUP, "email": email})
    assert r.status_code == 201, r.json()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def staff(db, hospital: Hospital) -> dict:
    t = db.query(Tenant).filter_by(hospital_id=hospital.id).one()
    return {"Authorization": f"Bearer {create_access_token(str(uuid.uuid4()), 'staff', tenant_id=str(t.id))}"}


def post(client, h, headers, **kw):
    return client.post(f"/api/v1/hospitals/{h.id}/booking-requests", json=body(**kw), headers=headers)


# ---------- 예약 요청 ----------


def test_예약_요청은_pending으로_만들어지고_동의가_요청서에_묶인다(client, db):
    h, me = make_hospital(db), patient(client)
    r = post(client, h, me, message="想做雷射淨膚",
             consents=[{"kind": "privacy", "version": "2026-11-03"}, {"kind": "overseas_transfer", "version": "2026-11-18"}])
    assert r.status_code == 201, r.json()
    d = r.json()
    assert d["status"] == "pending" and d["hospital_id"] == h.id
    assert d["message_original"] == "想做雷射淨膚"
    kinds = {c.kind for c in db.query(Consent).filter(Consent.booking_request_id == uuid.UUID(d["id"]))}
    assert kinds == {"privacy", "overseas_transfer"}


def test_로그인_없이_요청하면_401(client, db):
    h = make_hospital(db)
    assert client.post(f"/api/v1/hospitals/{h.id}/booking-requests", json=body()).status_code == 401


def test_직원_토큰으로_요청하면_403(client, db):
    h = make_hospital(db)
    assert post(client, h, staff(db, h)).status_code == 403


def test_등록_안된_병원_영업_중_아닌_병원은_403(client, db):
    me = patient(client)
    r = post(client, make_hospital(db, registered=False), me)
    assert (r.status_code, r.json()["code"], r.json()["detail"]["reason"]) == (403, "hospital.not_requestable", "unregistered")
    r = post(client, make_hospital(db, verdict="closed"), me)
    assert r.json()["detail"]["reason"] == "not_operating"


def test_입점_안한_등록_병원은_403_not_joined(client, db):
    r = post(client, make_hospital(db, tenant=False), patient(client))
    assert (r.status_code, r.json()["code"], r.json()["detail"]["reason"]) == (403, "hospital.not_requestable", "not_joined")


def test_없는_병원은_404(client, db):
    assert post(client, type("H", (), {"id": 999999})(), patient(client)).status_code == 404


def test_privacy_동의가_없으면_422_consent_required(client, db):
    r = post(client, make_hospital(db), patient(client), consents=[])
    assert (r.status_code, r.json()["code"]) == (422, "consent.required")
    assert "privacy" in r.json()["detail"]["missing"]


def test_건강정보가_있으면_health_동의_필요(client, db):
    r = post(client, make_hospital(db), patient(client), health_info="아토피 있음",
             consents=[{"kind": "privacy", "version": "2026-11-03"}, {"kind": "overseas_transfer", "version": "2026-11-18"}])
    assert (r.status_code, r.json()["code"]) == (422, "consent.required")
    assert r.json()["detail"]["missing"] == ["health"]


def test_메시지가_있으면_번역용_overseas_transfer_동의_필요(client, db):
    r = post(client, make_hospital(db), patient(client), message="hello")
    assert r.json()["detail"]["missing"] == ["overseas_transfer"]


def test_국내_거주는_요청_불가_422(client, db):
    r = post(client, make_hospital(db), patient(client), residency="resident")
    assert (r.status_code, r.json()["code"]) == (422, "validation")


def test_희망_시간은_1_3개_미래만(client, db):
    h, me = make_hospital(db), patient(client)
    assert post(client, h, me, preferred_slots=[]).status_code == 422
    assert post(client, h, me, preferred_slots=[slot(1), slot(2), slot(3), slot(4)]).status_code == 422
    assert post(client, h, me, preferred_slots=[slot(-1)]).status_code == 422


def test_진료시간_밖_희망_일시는_422(client, db):
    """휴진일·진료 전후·점심이면 거절, 몇 번째 희망 일시인지 알려 줌. 진료시간 데이터가 없는 날은 막지 않음."""
    from datetime import time as dtime
    from zoneinfo import ZoneInfo

    from modules.hospital.models import HospitalHours

    h, me = make_hospital(db), patient(client)
    days = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
    for i, d in enumerate(days):
        closed = d == "sun"
        db.add(HospitalHours(hospital_id=h.id, day=d, day_order=i, state="closed" if closed else "open", source="테스트",
                             checked_at=utcnow(), open_time=None if closed else dtime(9, 30), close_time=None if closed else dtime(18, 30),
                             lunch_start=None if closed else dtime(13), lunch_end=None if closed else dtime(14)))
    db.commit()
    kst = ZoneInfo("Asia/Seoul")
    base = datetime.now(kst).date() + timedelta(days=7)
    mon = base + timedelta(days=(0 - base.weekday()) % 7)  # 다음 월요일 이후
    at = lambda day, hh, mm=0: datetime(day.year, day.month, day.day, hh, mm, tzinfo=kst).astimezone(timezone.utc).isoformat()
    sun = mon + timedelta(days=6)

    r = post(client, h, me, preferred_slots=[at(mon, 10), at(sun, 10), at(mon, 13, 30), at(mon, 19)][:3])
    assert r.status_code == 422
    assert [e["loc"] for e in r.json()["detail"]["errors"]] == [["preferred_slots", 1], ["preferred_slots", 2]]
    assert post(client, h, me, preferred_slots=[at(mon, 19)]).status_code == 422  # 마감 뒤
    assert post(client, h, me, preferred_slots=[at(mon, 9)]).status_code == 422  # 시작 전
    assert post(client, h, me, preferred_slots=[at(mon, 10), at(mon, 18)]).status_code == 201


def test_진료시간_데이터가_없으면_막지_않음(client, db):
    h, me = make_hospital(db), patient(client)  # hospital_hours 없음
    assert post(client, h, me).status_code == 201


def test_같은_병원에_처리_안된_요청이_있으면_409(client, db):
    h, me = make_hospital(db), patient(client)
    assert post(client, h, me).status_code == 201
    r = post(client, h, me)
    assert (r.status_code, r.json()["code"]) == (409, "booking.duplicate")


# ---------- 내 예약 ----------


def test_내_예약_목록_상세는_내_것만(client, db):
    h = make_hospital(db)
    a, b = patient(client, "a@example.com"), patient(client, "b@example.com")
    rid = post(client, h, a).json()["id"]
    assert [x["id"] for x in client.get("/api/v1/me/booking-requests", headers=a).json()] == [rid]
    assert client.get("/api/v1/me/booking-requests", headers=b).json() == []
    assert client.get(f"/api/v1/me/booking-requests/{rid}", headers=a).status_code == 200
    assert client.get(f"/api/v1/me/booking-requests/{rid}", headers=b).status_code == 404  # 남의 요청


def test_병원이_확정하면_내_예약에_confirmed(client, db):
    h, me = make_hospital(db), patient(client)
    rid = post(client, h, me).json()["id"]
    s = client.post(f"/api/v1/tenant/booking-requests/{rid}/confirm", json={"slot": slot(3)}, headers=staff(db, h))
    assert s.status_code == 200, s.json()
    d = client.get(f"/api/v1/me/booking-requests/{rid}", headers=me).json()
    assert d["status"] == "confirmed" and d["confirmed_slot"]


def test_제안_수락과_취소(client, db):
    h, me = make_hospital(db), patient(client)
    rid = post(client, h, me).json()["id"]
    # pending에서 수락은 안 됨
    assert client.post(f"/api/v1/me/booking-requests/{rid}/accept", headers=me).status_code == 409
    client.post(f"/api/v1/tenant/booking-requests/{rid}/propose", json={"slot": slot(4)}, headers=staff(db, h))
    assert client.post(f"/api/v1/me/booking-requests/{rid}/accept", headers=me).json()["status"] == "confirmed"
    # 확정 뒤 취소는 안 됨 (contracts 2절)
    assert client.post(f"/api/v1/me/booking-requests/{rid}/cancel", json={}, headers=me).status_code == 409


def test_취소_사유_코드(client, db):
    h, me = make_hospital(db), patient(client)
    rid = post(client, h, me).json()["id"]
    assert client.post(f"/api/v1/me/booking-requests/{rid}/cancel", json={"reason": "bad"}, headers=me).status_code == 422
    r = client.post(f"/api/v1/me/booking-requests/{rid}/cancel", json={"reason": "schedule"}, headers=me)
    assert r.json()["status"] == "cancelled"
    # 취소했으니 같은 병원에 다시 요청 가능
    assert post(client, h, me).status_code == 201


def test_거절되면_내_예약에_거절_사유_코드(client, db):
    h, me = make_hospital(db), patient(client)
    rid = post(client, h, me).json()["id"]
    assert client.get(f"/api/v1/me/booking-requests/{rid}", headers=me).json()["reject_reason"] is None
    r = client.post(f"/api/v1/tenant/booking-requests/{rid}/reject", json={"reason": "needs_consult"}, headers=staff(db, h))
    assert r.status_code == 200, r.json()
    mine = client.get("/api/v1/me/booking-requests", headers=me).json()[0]
    assert (mine["status"], mine["reject_reason"]) == ("rejected", "needs_consult")


def test_일본어_계정_상담_언어도_받는다(client, db):
    """프론트에 일본어 화면이 있어 가입·상담 언어로 ja를 받는다 (2026-11-26, 마이그레이션 0014)."""
    r = client.post("/api/v1/auth/patient/signup", json={**SIGNUP, "email": "ja@example.com", "preferred_lang": "ja"})
    assert r.status_code == 201, r.json()
    me = {"Authorization": f"Bearer {r.json()['access_token']}"}
    h = make_hospital(db)
    assert post(client, h, me, lang="ja").status_code == 201
