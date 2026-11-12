"""에러 형식: 처리하지 못한 예외도 {code, message, detail} 500으로, 로그에는 예외 종류만."""

import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.errors import register_error_handlers

SECRET_TEXT = "patient1@example.com 비밀 내용"


def _app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    def boom():
        raise RuntimeError(SECRET_TEXT)

    @app.get("/only-get")
    def only_get():
        return {"ok": True}

    return app


def test_unknown_path_is_api_not_found():
    # 리소스 없음(`not_found`)과 다른 코드: 프론트가 "서버에 이미 없음"으로 오해해 데이터를 지우지 않게
    r = TestClient(_app()).get("/no-such-path")
    assert r.status_code == 404
    assert r.json() == {"code": "api.not_found", "message": "없는 API 경로입니다", "detail": {}}


def test_wrong_method_is_api_method_not_allowed_with_allow_header():
    r = TestClient(_app()).post("/only-get")
    assert r.status_code == 405
    assert r.json()["code"] == "api.method_not_allowed"
    assert set(r.json()) == {"code", "message", "detail"}
    assert "GET" in r.headers["allow"]


def test_unhandled_exception_is_internal_500(caplog):
    client = TestClient(_app(), raise_server_exceptions=False)
    with caplog.at_level(logging.ERROR):
        r = client.get("/boom")
    assert r.status_code == 500
    body = r.json()
    assert body["code"] == "internal" and body["detail"] == {} and body["message"]
    assert SECRET_TEXT not in r.text
    # 로그에는 예외 종류만 (메시지·개인정보 X)
    assert "RuntimeError" in caplog.text
    assert SECRET_TEXT not in caplog.text
