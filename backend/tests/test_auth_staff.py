"""A: 병원 직원(입점 병원) 가입·로그인. 가입할 때 환자/병원을 나눔. 가상 값만 (example.com, 가상 병원)."""

import uuid

import pytest
from sqlalchemy.orm import Session

from core.db import utcnow
from core.security import decode_access_token as decode_token
from modules.auth import attempts
from modules.hospital.models import Hospital
from modules.tenant.models import StaffUser, Tenant

PW = "staff-password-1234"
CONSENTS = [{"kind": "terms", "version": "2026-11-03"}, {"kind": "privacy", "version": "2026-11-03"}]


@pytest.fixture
def db(db_engine):
    with Session(db_engine, expire_on_commit=False) as s:
        yield s


@pytest.fixture(autouse=True)
def _reset_attempts():
    attempts.reset_all()
    yield
    attempts.reset_all()


def hospital(db, registered=True, verdict="normal") -> Hospital:
    h = Hospital(ykiho=f"Y-{uuid.uuid4().hex[:8]}", name_ko="예시피부과의원", is_registered_facility=registered,
                 status_verdict=verdict, is_demo=True, source="테스트", fetched_at=utcnow())
    db.add(h)
    db.commit()
    return h


def signup(client, h, **kw):
    body = {"email": "owner@example.com", "password": PW, "hospital_id": h.id, "registration_no": "M-2099-03-08-0001",
            "consents": CONSENTS}
    body.update(kw)
    return client.post("/api/v1/auth/staff/signup", json=body)


def test_입점_가입하면_병원_계정과_대표_직원이_생기고_직원_토큰(client, db):
    h = hospital(db)
    r = signup(client, h)
    assert r.status_code == 201, r.json()
    tok = decode_token(r.json()["access_token"])
    assert tok.role == "staff" and tok.tenant_id
    t = db.get(Tenant, uuid.UUID(tok.tenant_id))
    assert (t.hospital_id, t.requests_enabled, t.registration_no) == (h.id, True, "M-2099-03-08-0001")
    s = db.get(StaffUser, uuid.UUID(tok.sub))
    assert (s.email, s.role) == ("owner@example.com", "owner") and s.password_hash != PW
    # 직원 토큰으로 병원 API 사용
    me = client.get("/api/v1/tenant/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.status_code == 200


def test_등록_안된_병원_영업_안하는_병원은_가입_403(client, db):
    r = signup(client, hospital(db, registered=False))
    assert (r.status_code, r.json()["code"]) == (403, "hospital.not_requestable")
    assert signup(client, hospital(db, verdict="closed"), email="b@example.com").status_code == 403


def test_없는_병원은_404(client, db):
    assert signup(client, type("H", (), {"id": 999999})()).status_code == 404


def test_이미_입점한_병원은_409(client, db):
    h = hospital(db)
    assert signup(client, h).status_code == 201
    r = signup(client, h, email="other@example.com")
    assert (r.status_code, r.json()["code"]) == (409, "auth.hospital_taken")


def test_같은_직원_이메일은_409(client, db):
    assert signup(client, hospital(db)).status_code == 201
    r = signup(client, hospital(db))
    assert (r.status_code, r.json()["code"]) == (409, "auth.email_taken")


def test_필수_동의_없으면_422(client, db):
    r = signup(client, hospital(db), consents=[CONSENTS[0]])
    assert (r.status_code, r.json()["code"]) == (422, "consent.required")


def test_등록번호_형식이_틀리면_422(client, db):
    assert signup(client, hospital(db), registration_no="abc").status_code == 422


def test_직원_로그인_성공과_실패는_같은_응답(client, db):
    signup(client, hospital(db))
    ok = client.post("/api/v1/auth/staff/login", json={"email": "OWNER@example.com", "password": PW})
    assert ok.status_code == 200 and decode_token(ok.json()["access_token"]).role == "staff"
    bad_pw = client.post("/api/v1/auth/staff/login", json={"email": "owner@example.com", "password": "wrong-pass"})
    no_user = client.post("/api/v1/auth/staff/login", json={"email": "none@example.com", "password": PW})
    assert bad_pw.status_code == no_user.status_code == 401
    assert bad_pw.json()["code"] == no_user.json()["code"] == "auth.invalid_credentials"


def test_환자_계정으로는_직원_로그인_안됨(client, db):
    client.post("/api/v1/auth/patient/signup", json={"email": "p@example.com", "password": PW, "age14_confirmed": True,
                                                    "consents": CONSENTS})
    r = client.post("/api/v1/auth/staff/login", json={"email": "p@example.com", "password": PW})
    assert r.status_code == 401


def test_비활성_직원은_로그인_안됨(client, db):
    signup(client, hospital(db))
    s = db.query(StaffUser).filter_by(email="owner@example.com").one()
    s.disabled_at = utcnow()
    db.commit()
    r = client.post("/api/v1/auth/staff/login", json={"email": "owner@example.com", "password": PW})
    assert r.status_code == 401


def test_직원_로그인_실패가_많으면_429(client, db):
    signup(client, hospital(db))
    for _ in range(5):
        client.post("/api/v1/auth/staff/login", json={"email": "owner@example.com", "password": "wrong-pass"})
    r = client.post("/api/v1/auth/staff/login", json={"email": "owner@example.com", "password": PW})
    assert (r.status_code, r.json()["code"]) == (429, "auth.too_many_attempts")
