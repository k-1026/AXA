"""정기 정리 API (POST·GET /api/v1/internal/purge): 비밀 값 헤더, 30일 지난 대화·죽은 로그인 세션 삭제."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.config import get_settings
from core.db import utcnow
from modules.auth.models import AuthSession
from modules.chatbot.models import ChatMessage, ChatSession

from test_auth_patient import auth, signup
from test_chat_tables import add_messages, make_patient, make_session

PURGE = "/api/v1/internal/purge"
SECRET = "test-cron-secret-0123456789abcdef"


@pytest.fixture
def cron_secret(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", SECRET)
    get_settings.cache_clear()
    return SECRET


def bearer(secret: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {secret}"}


def test_disabled_without_secret(client):
    r = client.post(PURGE, headers=bearer(SECRET))
    assert r.status_code == 404 and r.json()["code"] == "not_found"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong-secret-0123456789abcdef"}, {"Authorization": SECRET}])
def test_wrong_or_missing_secret_is_401(client, cron_secret, headers):
    r = client.post(PURGE, headers=headers)
    assert r.status_code == 401 and r.json()["code"] == "auth.required"


@pytest.mark.parametrize("method", ["post", "get"])  # Vercel Cron은 GET으로 부름
def test_purge_deletes_old_chats_and_dead_sessions(client, db_engine, cron_secret, method):
    live = signup(client)
    dead = client.post("/api/v1/auth/patient/login", json={"email": "patient1@example.com", "password": "test-password-1234"}).json()["access_token"]
    client.post("/api/v1/auth/patient/logout", headers=auth(dead))
    with Session(db_engine, expire_on_commit=False) as db:
        p = make_patient(db)
        old, new = make_session(db, p, title="old"), make_session(db, p, title="new")
        old.last_message_at = utcnow() - timedelta(days=31)
        db.commit()
        add_messages(db, old)
        add_messages(db, new)

    r = getattr(client, method)(PURGE, headers=bearer(SECRET))
    assert r.status_code == 200
    assert r.json() == {"chat_sessions": 1, "auth_sessions": 1}
    with Session(db_engine) as db:
        assert [s.title for s in db.scalars(select(ChatSession))] == ["new"]
        assert db.scalar(select(func.count()).select_from(ChatMessage)) == 2
        assert db.scalar(select(func.count()).select_from(AuthSession)) == 1
    assert client.get("/api/v1/me", headers=auth(live)).status_code == 200


def test_empty_secret_means_disabled(client, monkeypatch):
    """.env.example를 그대로 복사한 `CRON_SECRET=`(빈 값)이면 꺼짐 (서버 시작 실패 X)."""
    monkeypatch.setenv("CRON_SECRET", "")
    get_settings.cache_clear()
    assert client.post(PURGE, headers=bearer("")).status_code == 404
