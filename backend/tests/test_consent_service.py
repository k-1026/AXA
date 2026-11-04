"""consent.service.require() — B도 요청서 처리에서 호출."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from core.db import utcnow
from core.errors import AppError
from modules.consent import service
from modules.patient.models import Patient


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


def test_request_scoped_consent(db, patient):
    req_a, req_b = uuid.uuid4(), uuid.uuid4()
    service.record(db, patient.id, "health", "v1", "en", request_id=req_a)
    db.commit()
    service.require(db, patient.id, ["health"], request_id=req_a)
    with pytest.raises(AppError):
        service.require(db, patient.id, ["health"], request_id=req_b)


def test_naive_datetime_rejected(db):
    db.add(Patient(email="n@example.com", password_hash="x", age14_confirmed_at=datetime(2026, 1, 1)))
    with pytest.raises(Exception):
        db.commit()
    db.rollback()
    db.add(Patient(email="n@example.com", password_hash="x", age14_confirmed_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    db.commit()
