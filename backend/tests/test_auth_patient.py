"""환자 회원가입·로그인·/me. 이메일·비밀번호는 가상 값만 (example.com)."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.db import utcnow
from core.security import create_access_token
from modules.consent.models import Consent
from modules.patient.models import Patient

EMAIL = "patient1@example.com"
PASSWORD = "test-password-1234"
SIGNUP = {
    "email": EMAIL,
    "password": PASSWORD,
    "age14_confirmed": True,
    "preferred_lang": "zh-TW",
    "timezone": "Asia/Taipei",
    "consents": [{"kind": "terms", "version": "2026-11"}, {"kind": "privacy", "version": "2026-11"}],
}


def signup(client, **override) -> str:
    r = client.post("/api/v1/auth/patient/signup", json={**SIGNUP, **override})
    assert r.status_code == 201, r.json()
    return r.json()["access_token"]


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/api/v1/auth/patient/login", json={"email": email, "password": password})


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- 회원가입 ---


def test_signup_creates_patient_and_consents(client, db_engine):
    token = signup(client)
    me = client.get("/api/v1/me", headers=auth(token)).json()
    assert me["email"] == EMAIL
    assert (me["preferred_lang"], me["timezone"]) == ("zh-TW", "Asia/Taipei")
    assert "password" not in str(me)
    with Session(db_engine) as db:
        kinds = sorted(db.scalars(select(Consent.kind)))
        patient = db.scalar(select(Patient))
    assert kinds == ["privacy", "terms"]
    assert patient.age14_confirmed_at is not None


def test_password_stored_as_hash_only(client, db_engine):
    signup(client)
    with Session(db_engine) as db:
        stored = db.scalar(select(Patient.password_hash))
    assert PASSWORD not in stored
    assert stored.startswith("$argon2id$")


def test_email_normalized(client):
    signup(client, email="  Patient1@EXAMPLE.com ")
    assert login(client).status_code == 200


def test_duplicate_email_rejected(client):
    signup(client)
    r = client.post("/api/v1/auth/patient/signup", json={**SIGNUP, "email": "PATIENT1@example.com"})
    assert r.status_code == 409
    assert r.json()["code"] == "auth.email_taken"


def test_signup_under_14_rejected(client):
    r = client.post("/api/v1/auth/patient/signup", json={**SIGNUP, "age14_confirmed": False})
    assert r.status_code == 422
    assert r.json()["code"] == "consent.required"
    assert r.json()["detail"]["age14_confirmed"] is False


def test_signup_missing_privacy_rejected(client, db_engine):
    only_terms = [{"kind": "terms", "version": "2026-11"}]
    r = client.post("/api/v1/auth/patient/signup", json={**SIGNUP, "consents": only_terms})
    assert r.status_code == 422
    assert r.json()["detail"]["missing"] == ["privacy"]
    with Session(db_engine) as db:
        assert db.scalar(select(Patient)) is None  # 계정 안 만들어짐


@pytest.mark.parametrize(
    "override",
    [
        {"password": "short"},  # 8자 미만
        {"password": "x" * 129},
        {"email": "not-an-email"},
        {"timezone": "Mars/Base"},
        {"preferred_lang": "fr"},
    ],
)
def test_signup_invalid_input(client, override):
    r = client.post("/api/v1/auth/patient/signup", json={**SIGNUP, **override})
    assert r.status_code == 422
    assert r.json()["code"] == "validation"


# --- 로그인 ---


def test_login_ok(client):
    signup(client)
    r = login(client)
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert client.get("/api/v1/me", headers=auth(token)).status_code == 200


@pytest.mark.parametrize(
    "email,password", [(EMAIL, "wrong-password-99"), ("nobody@example.com", PASSWORD)]
)
def test_login_failure_same_response(client, email, password):
    signup(client)
    r = login(client, email, password)
    assert r.status_code == 401
    assert r.json()["code"] == "auth.invalid_credentials"
    assert r.json()["message"] == "이메일 또는 비밀번호가 맞지 않습니다"


# --- 로그아웃 ---


def test_logout_invalidates_token_immediately(client):
    token = signup(client)
    assert client.get("/api/v1/me", headers=auth(token)).status_code == 200
    r = client.post("/api/v1/auth/patient/logout", headers=auth(token))
    assert r.status_code == 204
    r = client.get("/api/v1/me", headers=auth(token))
    assert r.status_code == 401
    assert r.json()["code"] == "auth.required"
    # 같은 토큰으로 다시 로그아웃해도 401
    assert client.post("/api/v1/auth/patient/logout", headers=auth(token)).status_code == 401


def test_logout_keeps_other_sessions(client):
    phone = signup(client)
    laptop = login(client).json()["access_token"]
    client.post("/api/v1/auth/patient/logout", headers=auth(phone))
    assert client.get("/api/v1/me", headers=auth(phone)).status_code == 401
    assert client.get("/api/v1/me", headers=auth(laptop)).status_code == 200


def test_login_again_after_logout(client):
    token = signup(client)
    client.post("/api/v1/auth/patient/logout", headers=auth(token))
    new = login(client).json()["access_token"]
    assert client.get("/api/v1/me", headers=auth(new)).status_code == 200


def test_logout_requires_login(client):
    assert client.post("/api/v1/auth/patient/logout").status_code == 401


def test_login_purges_dead_sessions_of_that_patient(client, db_engine):
    from datetime import timedelta

    from modules.auth.models import AuthSession

    old = signup(client)  # 1: 로그아웃할 세션
    client.post("/api/v1/auth/patient/logout", headers=auth(old))
    live = login(client).json()["access_token"]  # 2: 살아 있는 세션
    other = signup(client, email="patient2@example.com")  # 다른 환자
    client.post("/api/v1/auth/patient/logout", headers=auth(other))
    with Session(db_engine) as db:  # 2번을 만료된 것으로
        pid = db.scalar(select(Patient.id).where(Patient.email == EMAIL))
        first_live = db.scalars(select(AuthSession).where(AuthSession.patient_id == pid, AuthSession.revoked_at.is_(None))).one()
        first_live.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()

    new = login(client).json()["access_token"]
    with Session(db_engine) as db:
        mine = db.scalars(select(AuthSession).where(AuthSession.patient_id == pid)).all()
        assert len(mine) == 1  # 로그아웃한 것·만료된 것 삭제, 새 세션만
        assert db.scalar(select(func.count()).select_from(AuthSession).where(AuthSession.patient_id != pid)) == 1  # 다른 환자 것은 그대로
    assert client.get("/api/v1/me", headers=auth(new)).status_code == 200
    for t in (old, live):
        assert client.get("/api/v1/me", headers=auth(t)).status_code == 401


def test_purge_dead_all(client, db_engine):
    from modules.auth import sessions

    a = signup(client)
    b = login(client).json()["access_token"]
    client.post("/api/v1/auth/patient/logout", headers=auth(a))  # 로그인 뒤 로그아웃 → 남아 있음
    with Session(db_engine) as db:
        assert sessions.purge_dead(db) == 1
        db.commit()
    assert client.get("/api/v1/me", headers=auth(b)).status_code == 200


def test_revoke_all_logs_out_every_device(client, db_engine):
    from modules.auth import sessions

    a = signup(client)
    b = login(client).json()["access_token"]
    with Session(db_engine) as db:
        sessions.revoke_all(db, db.scalar(select(Patient.id)))
        db.commit()  # sessions.*는 commit하지 않음 (부르는 쪽이)
    for t in (a, b):
        assert client.get("/api/v1/me", headers=auth(t)).status_code == 401


def test_session_functions_do_not_commit(client, db_engine):
    """auth/sessions.py는 commit하지 않음 → 부르는 쪽이 다른 변경과 한 번에 commit·rollback."""
    from modules.auth import sessions
    from modules.auth.models import AuthSession

    token = signup(client)
    with Session(db_engine) as db:
        sid = db.scalar(select(AuthSession.id))
        sessions.revoke(db, sid)
        sessions.revoke_all(db, db.scalar(select(Patient.id)))
        db.rollback()
    assert client.get("/api/v1/me", headers=auth(token)).status_code == 200


def test_session_of_other_patient_rejected(client):
    """토큰 sub를 다른 환자로 바꿔 서명해도 세션 주인과 달라서 401."""
    from core.security import decode_access_token

    a = signup(client)
    b_token = signup(client, email="patient2@example.com")
    a_sid = decode_access_token(a).sid
    b_sub = decode_access_token(b_token).sub
    forged = create_access_token(b_sub, "patient", session_id=a_sid)
    assert client.get("/api/v1/me", headers=auth(forged)).status_code == 401


# --- /me ---


def test_me_requires_login(client):
    r = client.get("/api/v1/me")
    assert r.status_code == 401
    assert r.json()["code"] == "auth.required"


def test_me_rejects_staff_token(client):
    token = create_access_token("staff-1", "staff", tenant_id="tenant-1")
    assert client.get("/api/v1/me", headers=auth(token)).status_code == 403


def test_me_token_with_non_uuid_sub(client):
    token = create_access_token("abc", "patient", session_id="xyz")
    r = client.get("/api/v1/me", headers=auth(token))
    assert r.status_code == 401


def test_patch_me(client):
    token = signup(client)
    r = client.patch(
        "/api/v1/me",
        headers=auth(token),
        json={"preferred_lang": "vi", "timezone": "Asia/Ho_Chi_Minh", "display_name": "Lan"},
    )
    assert r.status_code == 200
    body = r.json()
    assert (body["preferred_lang"], body["timezone"], body["display_name"]) == (
        "vi",
        "Asia/Ho_Chi_Minh",
        "Lan",
    )


@pytest.mark.parametrize(
    "payload", [{"timezone": "Mars/Base"}, {"preferred_lang": "fr"}, {"timezone": None}]
)
def test_patch_me_invalid(client, payload):
    token = signup(client)
    r = client.patch("/api/v1/me", headers=auth(token), json=payload)
    assert r.status_code == 422
    assert r.json()["code"] == "validation"


def test_patch_me_cannot_change_password_or_email(client):
    token = signup(client)
    r = client.patch(
        "/api/v1/me", headers=auth(token), json={"email": "x@example.com", "password_hash": "x"}
    )
    assert r.status_code == 200
    assert r.json()["email"] == EMAIL
    assert login(client).status_code == 200


def test_signup_with_display_name(client):
    token = signup(client, display_name="  Lan  ")
    assert client.get("/api/v1/me", headers=auth(token)).json()["display_name"] == "Lan"


def test_signup_blank_display_name_is_null(client):
    token = signup(client, display_name="   ")
    assert client.get("/api/v1/me", headers=auth(token)).json()["display_name"] is None


def test_cors_allows_frontend_origin(client):
    r = client.options(
        "/api/v1/auth/patient/login",
        headers={
            "Origin": "http://localhost:5403",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5403"


def test_cors_blocks_unknown_origin(client):
    r = client.get("/api/v1/health", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in r.headers


# --- 탈퇴 ---


def withdraw(client, token, password=PASSWORD):
    return client.request("DELETE", "/api/v1/me", headers=auth(token), json={"password": password})


def test_withdraw_deletes_account_immediately(client, db_engine):
    from modules.auth.models import AuthSession

    a = signup(client)
    b = login(client).json()["access_token"]
    other = signup(client, email="patient2@example.com")
    assert withdraw(client, a).status_code == 204
    for t in (a, b):
        assert client.get("/api/v1/me", headers=auth(t)).status_code == 401
    assert login(client).status_code == 401
    with Session(db_engine) as db:
        emails = db.scalars(select(Patient.email)).all()
        assert emails == ["patient2@example.com"]  # 내 계정 행은 없음
        assert db.scalar(select(func.count()).select_from(AuthSession)) == 1  # 다른 환자 세션만
        consents = db.scalars(select(Consent)).all()
        assert len(consents) == 4  # 동의 기록은 남김 (증명)
        assert sum(c.patient_id is None for c in consents) == 2  # 내 것은 누구 것인지 비움
    assert client.get("/api/v1/me", headers=auth(other)).status_code == 200
    signup(client)  # 같은 메일로 바로 재가입


def test_withdraw_wrong_password(client):
    token = signup(client)
    r = withdraw(client, token, "wrong-password-99")
    assert r.status_code == 401
    assert r.json()["code"] == "auth.invalid_credentials"
    assert client.get("/api/v1/me", headers=auth(token)).status_code == 200  # 그대로


def test_withdraw_requires_login(client):
    r = client.request("DELETE", "/api/v1/me", json={"password": PASSWORD})
    assert r.status_code == 401


def test_signup_race_on_same_email_is_409(client, monkeypatch):
    """두 요청이 동시에 '없음'을 확인하고 넣으면 DB 유일 제약이 막음 → 500 대신 409."""
    from modules.patient import service as patient_service

    signup(client)
    monkeypatch.setattr(patient_service, "get_by_email", lambda db, email: None)  # 확인을 지나친 두 번째 요청
    r = client.post("/api/v1/auth/patient/signup", json=SIGNUP)
    assert r.status_code == 409
    assert r.json()["code"] == "auth.email_taken"
