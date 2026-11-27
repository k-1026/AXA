"""A: 체류 형태(국내 거주 여부) — 가입 때 거주국 + 3문항, 예약 요청 때 다시 확인 (compliance 2-1, 결정 28).

국내 거주 외국인은 유치 대상이 아님 (의료법 제27조 제3항 제2호, 시행규칙 제19조의2) → 정보 열람만.
가상 데이터만 (example.com, 가상 병원).
"""

import pytest
from sqlalchemy.orm import Session

from test_booking_patient import SIGNUP, body, make_hospital

API = "/api/v1"
VISITOR = {"country": "TW", "alien_registration": False, "domestic_residence": False, "health_insurance": False}


@pytest.fixture
def db(db_engine):
    with Session(db_engine, expire_on_commit=False) as s:
        yield s


def signup(client, residency=None, email="r@example.com") -> dict:
    data = {**SIGNUP, "email": email}
    data.pop("residency", None)
    if residency is not None:
        data["residency"] = residency
    r = client.post(f"{API}/auth/patient/signup", json=data)
    assert r.status_code == 201, r.json()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def me(client, h) -> dict:
    return client.get(f"{API}/me", headers=h).json()


def book(client, hospital, h):
    return client.post(f"{API}/hospitals/{hospital.id}/booking-requests", json=body(), headers=h)


def test_가입_때_3문항_모두_아니오면_단기_방문(client):
    out = me(client, signup(client, VISITOR))
    assert (out["residency"], out["residence_country"]) == ("short_term", "TW")


@pytest.mark.parametrize("field", ["alien_registration", "domestic_residence", "health_insurance"])
def test_하나라도_예면_국내_거주(client, field):
    assert me(client, signup(client, {**VISITOR, field: True}))["residency"] == "resident"


def test_거주국이_한국이면_국내_거주(client):
    assert me(client, signup(client, {**VISITOR, "country": "KR"}))["residency"] == "resident"


def test_예전_가입처럼_안_보내면_비어_있음(client):
    assert me(client, signup(client))["residency"] is None


def test_거주국은_ISO_2자리만(client):
    data = {**SIGNUP, "email": "bad@example.com", "residency": {**VISITOR, "country": "Taiwan"}}
    assert client.post(f"{API}/auth/patient/signup", json=data).status_code == 422


def test_마이페이지에서_다시_답할_수_있음(client):
    h = signup(client)
    r = client.put(f"{API}/me/residency", json=VISITOR, headers=h)
    assert r.status_code == 200 and r.json()["residency"] == "short_term"
    r = client.put(f"{API}/me/residency", json={**VISITOR, "health_insurance": True}, headers=h)
    assert r.json()["residency"] == "resident"


def test_거주_답은_로그인해야(client):
    assert client.put(f"{API}/me/residency", json=VISITOR).status_code == 401


def test_단기_방문이면_예약_요청_가능(client, db):
    assert book(client, make_hospital(db), signup(client, VISITOR)).status_code == 201


def test_답이_없으면_예약_요청_422_residency_required(client, db):
    r = book(client, make_hospital(db), signup(client))
    assert (r.status_code, r.json()["code"]) == (422, "residency.required")


def test_국내_거주면_예약_요청_403_not_eligible(client, db):
    r = book(client, make_hospital(db), signup(client, {**VISITOR, "alien_registration": True}))
    assert (r.status_code, r.json()["code"]) == (403, "residency.not_eligible")


def test_답을_고치면_바로_반영(client, db):
    h, hospital = signup(client), make_hospital(db)
    assert book(client, hospital, h).status_code == 422
    client.put(f"{API}/me/residency", json=VISITOR, headers=h)
    assert book(client, hospital, h).status_code == 201


def test_브라우저_사전_요청에서_PUT_허용(client):
    r = client.options(f"{API}/me/residency", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "PUT",
        "Access-Control-Request-Headers": "authorization,content-type"})
    assert r.status_code == 200 and "PUT" in r.headers["access-control-allow-methods"]


# --- 국적 (11/27, 결정 36): 한국 국적이면 해외에 살아도 국내 거주 취급 ---
def test_한국_국적이면_해외_거주여도_국내_거주_취급(client):
    assert me(client, signup(client, {**VISITOR, "nationality": "KR"}))["residency"] == "resident"
    assert me(client, signup(client, {**VISITOR, "nationality": "TW"}, email="tw@example.com"))["residency"] == "short_term"


def test_국적은_ISO_2자리만_그리고_저장하지_않음(client):
    data = {**SIGNUP, "email": "bad2@example.com", "residency": {**VISITOR, "nationality": "Korea"}}
    assert client.post(f"{API}/auth/patient/signup", json=data).status_code == 422
    assert "nationality" not in me(client, signup(client, {**VISITOR, "nationality": "JP"}, email="jp@example.com"))


def test_요청서_국적이_한국이면_403(client, db):
    r = client.post(f"{API}/hospitals/{make_hospital(db).id}/booking-requests", json=body(nationality="KR"),
                    headers=signup(client, VISITOR))
    assert r.status_code == 403
    assert (r.json()["code"], r.json()["detail"]["reason"]) == ("residency.not_eligible", "korean_nationality")
