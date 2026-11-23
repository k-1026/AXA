"""병원 직원 상담 답장 — POST /tenant/booking-requests/{id}/replies, 병원 목록·상세의 replies, 환자 쪽 replies."""

import uuid

import pytest
from sqlalchemy.orm import Session

from core.security import create_access_token
from modules.booking.models import Reply
from modules.tenant.models import StaffUser, Tenant
from test_booking_patient import make_hospital, patient, post

API = "/api/v1"


@pytest.fixture
def db(db_engine):
    with Session(db_engine, expire_on_commit=False) as s:
        yield s


def staff_of(db, hospital) -> tuple[dict, StaffUser]:
    t = db.query(Tenant).filter_by(hospital_id=hospital.id).one()
    s = StaffUser(tenant_id=t.id, email=f"st-{uuid.uuid4().hex[:6]}@example.com", password_hash="x", role="owner")
    db.add(s)
    db.commit()
    token = create_access_token(str(s.id), "staff", tenant_id=str(t.id))
    return {"Authorization": f"Bearer {token}"}, s


def test_reply_is_saved_and_shown_to_staff_and_patient(client, db):
    h = make_hospital(db)
    p = patient(client)
    s, staff_user = staff_of(db, h)
    req_id = post(client, h, p).json()["id"]

    r = client.post(f"{API}/tenant/booking-requests/{req_id}/replies", json={"text": "  네, 21일 오전 가능해요  "}, headers=s)
    assert r.status_code == 201, r.json()
    assert r.json()["text_ko"] == "네, 21일 오전 가능해요" and r.json()["sent_at"]
    saved = db.get(Reply, uuid.UUID(r.json()["id"]))
    assert saved.approved_by == staff_user.id and saved.ai_draft is False  # 보낸 직원 = 승인자

    # 병원 목록·상세에 붙음
    lst = client.get(f"{API}/tenant/booking-requests", headers=s).json()
    assert [x["text_ko"] for x in lst[0]["replies"]] == ["네, 21일 오전 가능해요"]
    one = client.get(f"{API}/tenant/booking-requests/{req_id}", headers=s).json()
    assert len(one["replies"]) == 1
    # 환자 내 예약에도 보임
    mine = client.get(f"{API}/me/booking-requests/{req_id}", headers=p).json()
    assert [x["text_ko"] for x in mine["replies"]] == ["네, 21일 오전 가능해요"]


def test_other_hospital_cannot_reply_or_see(client, db):
    h1, h2 = make_hospital(db), make_hospital(db)
    p = patient(client)
    s2, _ = staff_of(db, h2)
    req_id = post(client, h1, p).json()["id"]

    r = client.post(f"{API}/tenant/booking-requests/{req_id}/replies", json={"text": "안녕하세요"}, headers=s2)
    assert r.status_code == 404
    assert client.get(f"{API}/tenant/booking-requests", headers=s2).json() == []


def test_reply_validation_and_login(client, db):
    h = make_hospital(db)
    p = patient(client)
    s, _ = staff_of(db, h)
    req_id = post(client, h, p).json()["id"]
    url = f"{API}/tenant/booking-requests/{req_id}/replies"

    assert client.post(url, json={"text": "   "}, headers=s).status_code == 422  # 공백만
    assert client.post(url, json={"text": "가" * 2001}, headers=s).status_code == 422
    assert client.post(url, json={"text": "안녕하세요"}).status_code == 401  # 로그인 없이
    assert client.post(url, json={"text": "안녕하세요"}, headers=p).status_code in (401, 403)  # 환자 토큰


def test_unknown_staff_token_still_saves_without_approver(client, db):
    """토큰의 직원 행이 없으면(테스트·임시 토큰) 승인자 칸만 비움"""
    h = make_hospital(db)
    p = patient(client)
    t = db.query(Tenant).filter_by(hospital_id=h.id).one()
    s = {"Authorization": f"Bearer {create_access_token(str(uuid.uuid4()), 'staff', tenant_id=str(t.id))}"}
    req_id = post(client, h, p).json()["id"]
    r = client.post(f"{API}/tenant/booking-requests/{req_id}/replies", json={"text": "확인했어요"}, headers=s)
    assert r.status_code == 201
    assert db.get(Reply, uuid.UUID(r.json()["id"])).approved_by is None


def test_actions_still_work_next_to_replies_route(client, db):
    """/{action} 경로와 /replies 경로가 섞이지 않음"""
    h = make_hospital(db)
    p = patient(client)
    s, _ = staff_of(db, h)
    req_id = post(client, h, p).json()["id"]
    assert client.post(f"{API}/tenant/booking-requests/{req_id}/reject", json={}, headers=s).status_code == 200
    assert client.post(f"{API}/tenant/booking-requests/{req_id}/unknown", json={}, headers=s).status_code == 422
