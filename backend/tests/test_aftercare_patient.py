"""A: 환자용 사후관리 API (aftercare/router_patient). 가상 데이터만 (example.com, 가상 병원 9001).

흐름: 방문 완료(visited) → 환자가 첫 메시지(대화 열림) → 병원 답장 → 환자 화면에 답장·안 읽은 수
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from core.security import create_access_token
from db_rows import demo_hospital, demo_staff
from modules.aftercare import service as aftercare
from modules.booking import service as booking
from modules.patient.models import Patient
from modules.tenant.models import Tenant

NOW = datetime(2026, 11, 16, 3, 0, tzinfo=timezone.utc)
SLOT = "2026-11-21T01:00:00+00:00"
SIGNUP = {
    "password": "test-password-1234",
    "age14_confirmed": True,
    "preferred_lang": "zh-TW",
    "timezone": "Asia/Taipei",
    "consents": [{"kind": "terms", "version": "2026-11-03"}, {"kind": "privacy", "version": "2026-11-03"}],
}


@pytest.fixture
def db(db_engine):
    with Session(db_engine, expire_on_commit=False) as s:
        yield s


def _me(client, db, email="aftercare@example.com"):
    r = client.post("/api/v1/auth/patient/signup", json={**SIGNUP, "email": email})
    assert r.status_code == 201, r.json()
    p = db.query(Patient).filter_by(email=email).one()
    return p, {"Authorization": f"Bearer {r.json()['access_token']}"}


def _tenant(db, hid=9001, aftercare_on=True):
    demo_hospital(db, hid)
    t = Tenant(hospital_id=hid, display_name=f"가상 병원 {hid}", requests_enabled=True, aftercare_enabled=aftercare_on)
    db.add(t)
    db.commit()
    return t


def _req(db, p, t, visited=True):
    r = booking.create_request(
        db, p.id, t.id,
        dict(lang="zh-TW", nationality="TW", contact_method="email", preferred_slots=[SLOT],
             department_code="dermatology", treatment="laser_toning", visa_needed=False),
    )
    if visited:
        booking.staff_act(db, t.id, "s", r.id, "confirm", NOW)
        booking.staff_act(db, t.id, "s", r.id, "visited")
    return r


def _url(r):
    return f"/api/v1/me/booking-requests/{r.id}/aftercare"


def test_보내면_대화가_열리고_병원_답장이_안읽은_수로_보인다(client, db):
    (p, me), t = _me(client, db), _tenant(db)
    staff = demo_staff(db, t.id)
    r = _req(db, p, t)

    assert client.get(_url(r), headers=me).status_code == 404  # 아직 대화 없음
    out = client.post(_url(r) + "/messages", json={"text": "第三天了，臉還是有點紅", "photo": True}, headers=me)
    assert out.status_code == 201, out.json()
    d = out.json()
    assert d["status"] == "new" and [m["sender"] for m in d["messages"]] == ["patient"]
    assert d["messages"][0]["has_photo"] is True

    aftercare.tenant_reply(db, t.id, str(staff.id), uuid.UUID(d["id"]), "사진 확인했어요")
    lst = client.get("/api/v1/me/aftercare", headers=me).json()
    assert len(lst) == 1 and lst[0]["request_id"] == str(r.id)
    assert lst[0]["unread"] == 1 and lst[0]["last_message"] == "사진 확인했어요"

    d = client.get(_url(r), headers=me).json()
    assert [m["sender"] for m in d["messages"]] == ["patient", "staff"]

    # 다시 보내면 같은 대화에 이어지고 안 읽은 수는 0
    client.post(_url(r) + "/messages", json={"text": "謝謝"}, headers=me)
    lst = client.get("/api/v1/me/aftercare", headers=me).json()
    assert len(lst) == 1 and lst[0]["unread"] == 0


def test_방문_전이거나_사후관리_미지원_병원이면_409(client, db):
    (p, me), t = _me(client, db), _tenant(db)
    r = client.post(_url(_req(db, p, t, visited=False)) + "/messages", json={"text": "질문"}, headers=me)
    assert (r.status_code, r.json()["code"]) == (409, "booking.invalid_transition")

    off = _tenant(db, 9002, aftercare_on=False)
    r = client.post(_url(_req(db, p, off)) + "/messages", json={"text": "질문"}, headers=me)
    assert r.status_code == 409


def test_남의_요청서_대화는_404(client, db):
    (p, me), t = _me(client, db), _tenant(db)
    other, other_h = _me(client, db, "other@example.com")
    r = _req(db, p, t)
    client.post(_url(r) + "/messages", json={"text": "질문"}, headers=me)

    assert client.get(_url(r), headers=other_h).status_code == 404
    assert client.post(_url(r) + "/messages", json={"text": "x"}, headers=other_h).status_code == 404
    assert client.get("/api/v1/me/aftercare", headers=other_h).json() == []


def test_빈_메시지는_422(client, db):
    (p, me), t = _me(client, db), _tenant(db)
    r = client.post(_url(_req(db, p, t)) + "/messages", json={"text": "   "}, headers=me)
    assert (r.status_code, r.json()["code"]) == (422, "validation")


def test_로그인_없으면_401_직원_토큰이면_403(client, db):
    assert client.get("/api/v1/me/aftercare").status_code == 401
    tok = create_access_token(str(uuid.uuid4()), "staff", tenant_id=str(uuid.uuid4()))
    assert client.get("/api/v1/me/aftercare", headers={"Authorization": f"Bearer {tok}"}).status_code == 403


# ---------- 사진·영상 (Supabase Storage, 실제 호출은 가짜로 바꿈) ----------


@pytest.fixture
def storage(monkeypatch):
    from modules.media import service as media

    calls = {"upload": [], "view": []}
    monkeypatch.setattr(media, "enabled", lambda: True)

    def sign_upload(path):
        calls["upload"].append(path)
        return f"https://storage.example.test/upload/{path}?token=t"

    def sign_views(paths):
        calls["view"].append(list(paths))
        return {p: f"https://storage.example.test/view/{p}?token=v" for p in paths}

    monkeypatch.setattr(media, "sign_upload", sign_upload)
    monkeypatch.setattr(media, "sign_views", sign_views)
    return calls


def test_사진을_올리고_보내면_환자와_병원_모두_서명된_주소로_본다(client, db, storage):
    (p, me), t = _me(client, db), _tenant(db)
    r = _req(db, p, t)
    up = client.post(_url(r) + "/uploads", json={"name": "내 얼굴.JPG", "content_type": "image/jpeg", "size": 1234}, headers=me)
    assert up.status_code == 201, up.json()
    u = up.json()
    assert u["kind"] == "image" and u["path"].startswith(f"{t.id}/{r.id}/") and u["path"].endswith(".jpg")
    assert "얼굴" not in u["path"]  # 원래 파일 이름은 경로에 넣지 않음
    assert u["upload_url"].startswith("https://storage.example.test/upload/")

    out = client.post(_url(r) + "/messages", json={"text": "📷", "attachments": [{"path": u["path"], "kind": "image", "name": "내 얼굴.JPG"}]}, headers=me)
    assert out.status_code == 201, out.json()
    m = out.json()["messages"][0]
    assert m["has_photo"] is True
    assert m["attachments"] == [{"kind": "image", "name": "내 얼굴.JPG", "url": f"https://storage.example.test/view/{u['path']}?token=v"}]
    assert "path" not in m["attachments"][0]

    staff = demo_staff(db, t.id)
    tok = create_access_token(str(staff.id), "staff", tenant_id=str(t.id))
    th = client.get(f"/api/v1/tenant/aftercare/{out.json()['id']}", headers={"Authorization": f"Bearer {tok}"}).json()
    assert th["messages"][0]["attachments"][0]["url"].startswith("https://storage.example.test/view/")
    assert "path" not in th["messages"][0]["attachments"][0]


def test_다른_요청서_경로의_파일은_붙일_수_없다(client, db, storage):
    (p, me), t = _me(client, db), _tenant(db)
    r1, r2 = _req(db, p, t), _req(db, p, _tenant(db, 9002))
    other = client.post(_url(r2) + "/uploads", json={"content_type": "image/png", "size": 10}, headers=me).json()["path"]
    out = client.post(_url(r1) + "/messages", json={"text": "x", "attachments": [{"path": other, "kind": "image"}]}, headers=me)
    assert (out.status_code, out.json()["code"]) == (422, "validation")


def test_업로드_규칙_파일종류_크기_권한(client, db, storage):
    (p, me), t = _me(client, db), _tenant(db)
    _, other_h = _me(client, db, "other2@example.com")
    r = _req(db, p, t)
    assert client.post(_url(r) + "/uploads", json={"content_type": "application/pdf", "size": 10}, headers=me).status_code == 422
    assert client.post(_url(r) + "/uploads", json={"content_type": "video/mp4", "size": 50 * 1024 * 1024 + 1}, headers=me).status_code == 422
    assert client.post(_url(r) + "/uploads", json={"content_type": "video/mp4", "size": 10}, headers=other_h).status_code == 404
    before = _req(db, p, _tenant(db, 9003), visited=False)
    assert client.post(_url(before) + "/uploads", json={"content_type": "image/png", "size": 10}, headers=me).status_code == 409
    assert storage["upload"] == []  # 거절된 요청에는 업로드 주소를 만들지 않음


def test_저장소_설정이_없으면_503(client, db):
    (p, me), t = _me(client, db), _tenant(db)
    r = client.post(_url(_req(db, p, t)) + "/uploads", json={"content_type": "image/png", "size": 10}, headers=me)
    assert (r.status_code, r.json()["code"]) == (503, "storage.unavailable")


# ---------- 지우기 (결정 23) ----------


def _send_photo(client, me, r):
    path = client.post(_url(r) + "/uploads", json={"name": "a.png", "content_type": "image/png", "size": 10}, headers=me).json()["path"]
    out = client.post(_url(r) + "/messages", json={"text": "사진", "attachments": [{"path": path, "kind": "image"}]}, headers=me)
    assert out.status_code == 201, out.json()
    return path


def test_탈퇴하면_내_사진은_Storage에서_지우고_메시지는_사진_있음만_남는다(client, db, storage, monkeypatch):
    from modules.aftercare.models import AftercareMessage
    from modules.media import service as media

    removed = []
    monkeypatch.setattr(media, "remove", lambda paths: removed.extend(paths) or len(paths))
    (p, me), t = _me(client, db), _tenant(db)
    other, other_h = _me(client, db, "keep@example.com")
    mine = _send_photo(client, me, _req(db, p, t))
    theirs = _send_photo(client, other_h, _req(db, other, _tenant(db, 9002)))

    r = client.request("DELETE", "/api/v1/me", headers=me, json={"password": SIGNUP["password"]})
    assert r.status_code == 204
    assert removed == [mine]  # 남의 파일은 그대로
    db.expire_all()
    rows = db.query(AftercareMessage).all()
    gone = [m for m in rows if m.attachments == []]
    kept = [m for m in rows if m.attachments]
    assert len(gone) == 1 and gone[0].has_photo is True and gone[0].text_original == "사진"
    assert [a["path"] for a in kept[0].attachments] == [theirs]


def test_정기_정리는_DB에_없는_하루_지난_파일만_지운다(client, db, storage, monkeypatch):
    from datetime import timedelta

    from core.db import utcnow
    from modules.maintenance import service as maintenance
    from modules.media import service as media

    (p, me), t = _me(client, db), _tenant(db)
    used = _send_photo(client, me, _req(db, p, t))
    old, new = utcnow() - timedelta(days=2), utcnow() - timedelta(hours=1)
    monkeypatch.setattr(media, "list_objects", lambda: [(used, old), ("x/y/orphan-old.png", old), ("x/y/orphan-new.png", new)])
    removed = []
    monkeypatch.setattr(media, "remove", lambda paths: removed.extend(paths) or len(paths))
    assert maintenance.purge_media(db) == 1
    assert removed == ["x/y/orphan-old.png"]  # 쓰는 파일·방금 올린 파일은 남김


def test_정기_정리는_Storage_오류에도_멈추지_않는다(db, monkeypatch):
    from modules.maintenance import service as maintenance
    from modules.media import service as media

    monkeypatch.setattr(media, "enabled", lambda: True)
    monkeypatch.setattr(media, "list_objects", lambda: (_ for _ in ()).throw(RuntimeError("down")))
    assert maintenance.purge_media(db) == 0
