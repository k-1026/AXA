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

    return app


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
