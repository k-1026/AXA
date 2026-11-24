"""A: 웹 푸시 (결정 30) — 구독은 자기 것만, 알림이 commit된 뒤에만 푸시, 끝난 구독은 지움, 내용은 코드만. 가상 데이터만."""

import json

import pytest
from sqlalchemy.orm import Session

from core.config import get_settings
from modules.notification import push
from modules.notification.models import PushSubscription

from test_booking_patient import make_hospital, patient, post, slot, staff

API = "/api/v1"
SUB = {"endpoint": "https://push.example.test/sub/abc", "keys": {"p256dh": "BPkey", "auth": "authkey"}}


@pytest.fixture
def db(db_engine):
    with Session(db_engine, expire_on_commit=False) as s:
        yield s


@pytest.fixture
def vapid(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "vapid_public_key", "BPublicKeyForTest")
    monkeypatch.setattr(s, "vapid_private_key", "private-key-for-test")
    sent = []

    def fake_send(endpoint, p256dh, auth, payload):
        sent.append((endpoint, json.loads(payload)))
        return "gone" if endpoint.endswith("/gone") else "ok"

    monkeypatch.setattr(push, "send", fake_send)
    return sent


def test_키가_없으면_503(client):
    me = patient(client)
    assert client.get(f"{API}/me/push/key", headers=me).json()["code"] == "push.unavailable"
    assert client.post(f"{API}/me/push/subscriptions", json=SUB, headers=me).status_code == 503


def test_공개_키와_구독은_로그인해야(client, vapid):
    assert client.get(f"{API}/me/push/key").status_code == 401
    me = patient(client)
    assert client.get(f"{API}/me/push/key", headers=me).json() == {"public_key": "BPublicKeyForTest"}


def test_병원이_확정하면_구독한_브라우저에_코드만_푸시(client, db, vapid):
    h, me = make_hospital(db), patient(client)
    assert client.post(f"{API}/me/push/subscriptions", json=SUB, headers=me).status_code == 204
    rid = post(client, h, me).json()["id"]
    assert vapid == []  # 내가 요청만 한 상태에서는 푸시 없음
    client.post(f"{API}/tenant/booking-requests/{rid}/confirm", json={"slot": slot(3)}, headers=staff(db, h))
    assert vapid == [(SUB["endpoint"], {"kind": "status", "status": "confirmed", "request_id": rid, "lang": "zh-TW"})]


def test_rollback이면_푸시도_안_감(client, db, vapid):
    from modules.notification import service as notification
    from modules.patient.models import Patient
    import uuid

    me = patient(client)
    client.post(f"{API}/me/push/subscriptions", json=SUB, headers=me)
    p = db.query(Patient).one()
    rid = post(client, make_hospital(db), me).json()["id"]
    notification.notify(db, p.id, "reply", uuid.UUID(rid))
    db.rollback()
    db.commit()
    assert vapid == []


def test_끝난_구독은_지움(client, db, vapid):
    h, me = make_hospital(db), patient(client)
    client.post(f"{API}/me/push/subscriptions", json={**SUB, "endpoint": "https://push.example.test/gone"}, headers=me)
    client.post(f"{API}/me/push/subscriptions", json=SUB, headers=me)
    rid = post(client, h, me).json()["id"]
    client.post(f"{API}/tenant/booking-requests/{rid}/reject", json={}, headers=staff(db, h))
    assert len(vapid) == 2
    db.expire_all()
    assert [s.endpoint for s in db.query(PushSubscription).all()] == [SUB["endpoint"]]


def test_같은_브라우저로_다른_계정이_구독하면_옮겨지고_해제는_내_것만(client, db, vapid):
    a, b = patient(client, "a-push@example.com"), patient(client, "b-push@example.com")
    client.post(f"{API}/me/push/subscriptions", json=SUB, headers=a)
    client.post(f"{API}/me/push/subscriptions", json=SUB, headers=b)
    assert db.query(PushSubscription).count() == 1
    assert client.request("DELETE", f"{API}/me/push/subscriptions", json={"endpoint": SUB["endpoint"]}, headers=a).status_code == 204
    assert db.query(PushSubscription).count() == 1  # a는 이제 주인이 아님
    client.request("DELETE", f"{API}/me/push/subscriptions", json={"endpoint": SUB["endpoint"]}, headers=b)
    assert db.query(PushSubscription).count() == 0


def test_https_주소만_구독(client, vapid):
    me = patient(client)
    assert client.post(f"{API}/me/push/subscriptions", json={**SUB, "endpoint": "http://x"}, headers=me).status_code == 422


def test_실제_pywebpush로_암호화·서명하고_410은_gone(monkeypatch):
    """키 형식 확인: make_vapid_keys.py와 같은 형식(base64url)의 키로 실제 webpush 호출 (네트워크는 가짜)."""
    import base64
    import os

    import pywebpush
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    b64 = lambda raw: base64.urlsafe_b64encode(raw).rstrip(b"=").decode()  # noqa: E731
    server = ec.generate_private_key(ec.SECP256R1())
    browser = ec.generate_private_key(ec.SECP256R1()).public_key()
    s = get_settings()
    monkeypatch.setattr(s, "vapid_private_key", b64(server.private_numbers().private_value.to_bytes(32, "big")))
    monkeypatch.setattr(s, "vapid_public_key", "x")
    calls = []

    class Resp:
        def __init__(self, code):
            self.status_code, self.text, self.headers, self.reason, self.content = code, "", {}, "", b""

    def fake_post(url, data=None, headers=None, timeout=None, **kw):
        calls.append((url, headers))
        return Resp(410 if url.endswith("/gone") else 201)

    monkeypatch.setattr(pywebpush.requests, "post", fake_post)
    p256dh = b64(browser.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))
    auth = b64(os.urandom(16))
    assert push.send("https://push.example.test/ok", p256dh, auth, '{"kind":"reply"}') == "ok"
    assert push.send("https://push.example.test/gone", p256dh, auth, '{"kind":"reply"}') == "gone"
    url, headers = calls[0]
    assert headers["Authorization"].startswith("vapid t=") and headers["Content-Encoding"] == "aes128gcm"
