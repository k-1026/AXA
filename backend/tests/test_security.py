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
def app_client():
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
    data = decode_access_token(create_access_token("p1", "patient"))
    assert (data.sub, data.role, data.tenant_id) == ("p1", "patient", None)


def test_staff_token_requires_tenant():
    with pytest.raises(ValueError):
        create_access_token("s1", "staff")


def test_patient_token_rejects_tenant():
    with pytest.raises(ValueError):
        create_access_token("p1", "patient", tenant_id="t1")


def test_patient_route_ok(app_client):
    r = app_client.get("/patient-only", headers=auth(create_access_token("p1", "patient")))
    assert r.status_code == 200
    assert r.json() == {"patient_id": "p1"}


def test_no_token_is_401(app_client):
    r = app_client.get("/patient-only")
    assert r.status_code == 401
    assert r.json()["code"] == "auth.required"


def test_patient_token_on_staff_route_is_403(app_client):
    r = app_client.get("/staff-only", headers=auth(create_access_token("p1", "patient")))
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
