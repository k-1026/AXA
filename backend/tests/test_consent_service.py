"""consent.service.require() — B도 요청서 처리에서 호출."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.db import utcnow
from core.errors import AppError
from db_rows import demo_hospital
from modules.booking import service as booking
from modules.booking.models import BookingRequest
from modules.consent import service
from modules.consent.models import Consent
from modules.patient.models import Patient
from modules.tenant.models import Tenant


@pytest.fixture
def db(db_engine):
    with Session(db_engine) as s:
        yield s


@pytest.fixture
def patient(db):
    p = Patient(email="c@example.com", password_hash="x", age14_confirmed_at=utcnow())
    db.add(p)
    db.commit()
    return p


def test_require_passes_when_all_present(db, patient):
    service.record(db, patient.id, "terms", "v1", "en")
    service.record(db, patient.id, "privacy", "v1", "en")
    db.commit()
    service.require(db, patient.id, ["terms", "privacy"])


def test_require_lists_missing(db, patient):
    service.record(db, patient.id, "terms", "v1", "en")
    db.commit()
    with pytest.raises(AppError) as e:
        service.require(db, patient.id, ["terms", "health"])
    assert e.value.code == "consent.required"
    assert e.value.detail == {"missing": ["health"]}


def test_withdrawn_consent_does_not_count(db, patient):
    c = service.record(db, patient.id, "health", "v1", "en")
    db.commit()
    from modules.consent.models import Consent

    db.get(Consent, c.id).withdrawn_at = utcnow()
    db.commit()
    with pytest.raises(AppError):
        service.require(db, patient.id, ["health"])


def _request(db, patient, hospital_id: int = 9001) -> uuid.UUID:
    """booking_requests FK(0007) → 실제 요청서 행이 있어야 요청서별 동의를 저장할 수 있음.
    같은 환자 예약은 1시간 이내로 겹칠 수 없음(booking.time_conflict) → 요청서마다 병원·날짜를 다르게."""
    demo_hospital(db, hospital_id)
    tenant = db.query(Tenant).filter_by(hospital_id=hospital_id).one_or_none()
    if tenant is None:
        tenant = Tenant(hospital_id=hospital_id, display_name=f"가상 병원 {hospital_id}", requests_enabled=True)
        db.add(tenant)
        db.flush()
    r = booking.create_request(
        db, patient.id, tenant.id,
        dict(lang="en", nationality="TW", contact_method="email", preferred_slots=[f"2026-11-{21 + hospital_id - 9001:02d}T01:00:00Z"],
             department_code="dermatology", treatment="laser_toning", visa_needed=False),
    )
    return r.id


def test_request_scoped_consent(db, patient):
    req_a, req_b = _request(db, patient, 9001), _request(db, patient, 9002)
    service.record(db, patient.id, "health", "v1", "en", request_id=req_a)
    db.commit()
    service.require(db, patient.id, ["health"], request_id=req_a)
    with pytest.raises(AppError):
        service.require(db, patient.id, ["health"], request_id=req_b)


def test_요청서가_지워져도_동의_기록은_남는다(db, patient):
    req = _request(db, patient)
    service.record(db, patient.id, "health", "v1", "en", request_id=req)
    db.commit()
    db.delete(db.get(BookingRequest, req))
    db.commit()
    c = db.query(Consent).filter_by(patient_id=patient.id, kind="health").one()
    db.refresh(c)
    assert c.booking_request_id is None


def test_없는_요청서_id로는_동의를_저장할_수_없다(db, patient):
    with pytest.raises(IntegrityError):
        service.record(db, patient.id, "health", "v1", "en", request_id=uuid.uuid4())
    db.rollback()


def test_naive_datetime_rejected(db):
    db.add(Patient(email="n@example.com", password_hash="x", age14_confirmed_at=datetime(2026, 1, 1)))
    with pytest.raises(Exception):
        db.commit()
    db.rollback()
    db.add(Patient(email="n@example.com", password_hash="x", age14_confirmed_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    db.commit()
