"""A: media 서비스 — Supabase Storage 응답을 주소로 바꾸는 부분 (네트워크는 가짜)."""

import httpx
import pytest

from core.config import get_settings
from modules.media import service as media


@pytest.fixture
def on(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "supabase_url", "https://proj.supabase.example/")
    monkeypatch.setattr(s, "supabase_service_role_key", "service-key-for-test")


def _resp(status, body):
    return httpx.Response(status, json=body, request=httpx.Request("POST", "https://proj.supabase.example"))


def test_업로드_주소는_상대경로를_전체_주소로(monkeypatch, on):
    seen = {}

    def post(url, headers, timeout, **kw):
        seen.update(url=url, headers=headers)
        return _resp(200, {"url": "/object/upload/sign/aftercare-media/a/b.jpg?token=T"})

    monkeypatch.setattr(media.httpx, "post", post)
    assert media.sign_upload("a/b.jpg") == "https://proj.supabase.example/storage/v1/object/upload/sign/aftercare-media/a/b.jpg?token=T"
    assert seen["url"].endswith("/storage/v1/object/upload/sign/aftercare-media/a/b.jpg")
    assert seen["headers"]["Authorization"] == "Bearer service-key-for-test"


def test_새_형식_비밀_키는_apikey로만():
    assert media.headers("sb_secret_x") == {"apikey": "sb_secret_x"}
    assert media.headers("eyJ.a.b")["Authorization"] == "Bearer eyJ.a.b"


def test_업로드_주소_실패는_503(monkeypatch, on):
    monkeypatch.setattr(media.httpx, "post", lambda *a, **k: _resp(400, {"error": "Bucket not found"}))
    with pytest.raises(Exception) as e:
        media.sign_upload("a/b.jpg")
    assert e.value.code == "storage.unavailable"


def test_보기_주소는_실패한_파일만_빠짐(monkeypatch, on):
    body = [{"path": "a/1.jpg", "signedURL": "/object/sign/aftercare-media/a/1.jpg?token=V", "error": None},
            {"path": "a/2.jpg", "signedURL": None, "error": "Object not found"}]
    monkeypatch.setattr(media.httpx, "post", lambda *a, **k: _resp(200, body))
    assert media.sign_views(["a/1.jpg", "a/2.jpg", "a/1.jpg"]) == {
        "a/1.jpg": "https://proj.supabase.example/storage/v1/object/sign/aftercare-media/a/1.jpg?token=V"}


def test_설정이_없으면_보기_주소는_빈_값(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "supabase_url", None)
    assert media.enabled() is False and media.sign_views(["a/1.jpg"]) == {}


def test_지우기는_지운_수_실패하면_0(monkeypatch, on):
    seen = {}

    def request(method, url, headers, json, timeout):
        seen.update(method=method, url=url, json=json)
        return _resp(200, [{"name": "a/1.jpg"}])

    monkeypatch.setattr(media.httpx, "request", request)
    assert media.remove(["a/1.jpg", "a/1.jpg", ""]) == 1
    assert seen["method"] == "DELETE" and seen["url"].endswith("/object/aftercare-media") and seen["json"] == {"prefixes": ["a/1.jpg"]}
    monkeypatch.setattr(media.httpx, "request", lambda *a, **k: _resp(500, {}))
    assert media.remove(["a/1.jpg"]) == 0


def test_목록은_폴더를_따라_내려간다(monkeypatch, on):
    tree = {
        "": [{"name": "t1", "id": None}],
        "t1": [{"name": "r1", "id": None}],
        "t1/r1": [{"name": "f.png", "id": "x", "created_at": "2026-11-19T00:00:00.000Z"}],
    }
    monkeypatch.setattr(media.httpx, "post", lambda url, headers, timeout, json: _resp(200, tree[json["prefix"]]))
    [(path, created)] = media.list_objects()
    assert path == "t1/r1/f.png" and created.year == 2026 and created.tzinfo is not None


def test_썸네일_경로는_같은_폴더_확장자만_바꿈():
    assert media.thumb_path("t/r/abc.png") == "t/r/abc.thumb.jpg"
    assert media.thumb_path("t/r/abc") == "t/r/abc.thumb.jpg"
    assert media.with_thumbs(["t/r/a.jpg", ""]) == ["t/r/a.jpg", "t/r/a.thumb.jpg"]
