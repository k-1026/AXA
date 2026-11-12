"""GET /api/v1/health: 서버 + DB 연결 확인. DB에 연결할 수 없으면 503 `db.unavailable`."""

import logging

from sqlalchemy.exc import OperationalError

from core import db as core_db
from core.config import get_settings

SECRET_URL = "postgresql+psycopg://u:secret-password@db.example.com:6543/postgres"


def test_health_ok_checks_db(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": "ok"}


def test_health_db_connect_fails_is_503(client, monkeypatch, caplog):
    class _BrokenEngine:
        def connect(self):
            raise OperationalError("SELECT 1", {}, Exception(SECRET_URL))

    monkeypatch.setattr(core_db, "get_engine", lambda: _BrokenEngine())
    with caplog.at_level(logging.ERROR):
        r = client.get("/api/v1/health")
    assert r.status_code == 503
    assert r.json() == {"code": "db.unavailable", "message": "DB에 연결할 수 없습니다", "detail": {}}
    # 연결 문자열(비밀번호)은 응답·로그 어디에도 X
    assert "secret-password" not in r.text
    assert "OperationalError" in caplog.text
    assert "secret-password" not in caplog.text


def test_health_without_database_url_is_503(client, monkeypatch):
    # 빈 값 = 설정 안 됨 (루트 .env에 값이 있어도 환경변수가 우선)
    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()
    core_db.get_engine.cache_clear()
    r = client.get("/api/v1/health")
    assert r.status_code == 503
    assert r.json()["code"] == "db.unavailable"
