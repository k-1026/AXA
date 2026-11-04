from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from core.errors import register_error_handlers
from core.security import (
    PatientPrincipal,
    StaffPrincipal,
    create_access_token,
    current_patient,
    current_staff,
    decode_access_token,
)


@pytest.fixture
def app_client(db_engine):
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/patient-only")
    def patient_only(p: Annotated[PatientPrincipal, Depends(current_patient)]):
        return p.model_dump()

    @app.get("/staff-only")
    def staff_only(s: Annotated[StaffPrincipal, Depends(current_staff)]):
        return s.model_dump()

    return TestClient(app)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_patient_token_roundtrip():
    data = decode_access_token(create_access_token("p1", "patient", session_id="s1"))
    assert (data.sub, data.role, data.tenant_id, data.sid) == ("p1", "patient", None, "s1")


def test_patient_token_requires_session():
    with pytest.raises(ValueError):
        create_access_token("p1", "patient")


def test_staff_token_requires_tenant():
    with pytest.raises(ValueError):
        create_access_token("s1", "staff")


def test_patient_token_rejects_tenant():
    with pytest.raises(ValueError):
        create_access_token("p1", "patient", tenant_id="t1", session_id="s1")


def test_patient_route_ok(app_client, db_engine):
    from sqlalchemy.orm import Session

    from core.db import utcnow
    from core.security import token_expires_at
    from modules.auth import sessions
    from modules.patient.models import Patient

    with Session(db_engine) as db:
        p = Patient(email="s@example.com", password_hash="x", age14_confirmed_at=utcnow())
        db.add(p)
        db.flush()
        s = sessions.create(db, p.id, token_expires_at("patient"))
        db.commit()
        pid, sid = str(p.id), str(s.id)
    token = create_access_token(pid, "patient", session_id=sid)
    r = app_client.get("/patient-only", headers=auth(token))
    assert r.status_code == 200
    assert r.json() == {"patient_id": pid, "session_id": sid}


def test_patient_token_with_unknown_session_is_401(app_client):
    token = create_access_token(
        "00000000-0000-0000-0000-000000000001",
        "patient",
        session_id="00000000-0000-0000-0000-000000000002",
    )
    r = app_client.get("/patient-only", headers=auth(token))
    assert r.status_code == 401
    assert r.json()["code"] == "auth.required"


def test_no_token_is_401(app_client):
    r = app_client.get("/patient-only")
    assert r.status_code == 401
    assert r.json()["code"] == "auth.required"


def test_patient_token_on_staff_route_is_403(app_client):
    token = create_access_token("p1", "patient", session_id="s1")
    r = app_client.get("/staff-only", headers=auth(token))
    assert r.status_code == 403
    assert r.json()["code"] == "auth.forbidden"


def test_staff_token_on_patient_route_is_403(app_client):
    r = app_client.get("/patient-only", headers=auth(create_access_token("s1", "staff", "t1")))
    assert r.status_code == 403


def test_staff_route_returns_tenant(app_client):
    r = app_client.get("/staff-only", headers=auth(create_access_token("s1", "staff", "t1")))
    assert r.json() == {"staff_id": "s1", "tenant_id": "t1"}


def test_expired_token_is_401(app_client):
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    token = jwt.encode(
        {"sub": "p1", "role": "patient", "exp": past},
        "test-secret-not-for-real-use-0123456789abcdef",
        algorithm="HS256",
    )
    assert app_client.get("/patient-only", headers=auth(token)).status_code == 401


def test_wrong_secret_is_401(app_client):
    future = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = jwt.encode(
        {"sub": "p1", "role": "patient", "exp": future},
        "another-secret-that-is-also-long-enough-000000",
        algorithm="HS256",
    )
    assert app_client.get("/patient-only", headers=auth(token)).status_code == 401


def test_unknown_role_is_401(app_client):
    future = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = jwt.encode(
        {"sub": "x", "role": "admin", "exp": future},
        "test-secret-not-for-real-use-0123456789abcdef",
        algorithm="HS256",
    )
    assert app_client.get("/patient-only", headers=auth(token)).status_code == 401


def test_short_secret_rejected(monkeypatch):
    from pydantic import ValidationError

    from core.config import Settings

    monkeypatch.setenv("JWT_SECRET", "too-short")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("postgresql://u:p@h:6543/postgres", "postgresql+psycopg://u:p@h:6543/postgres"),
        ("postgres://u:p@h:5432/postgres", "postgresql+psycopg://u:p@h:5432/postgres"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("sqlite:///x.db", "sqlite:///x.db"),
    ],
)
def test_db_url_normalized(raw, expected):
    from core.db import normalize_db_url

    assert normalize_db_url(raw) == expected


def test_db_url_rejects_project_api_url():
    from core.db import normalize_db_url

    with pytest.raises(RuntimeError, match="Connection string"):
        normalize_db_url("https://example.supabase.co")
