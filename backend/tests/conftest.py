import pytest
from fastapi.testclient import TestClient

from core.config import get_settings
from core.db import Base, get_engine


@pytest.fixture(autouse=True)
def test_settings(monkeypatch):
    # 테스트는 .env 값과 상관없이 고정된 가짜 비밀 키 + 메모리 DB로
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-real-use-0123456789abcdef")
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    get_settings.cache_clear()
    get_engine.cache_clear()
    yield
    get_settings.cache_clear()
    get_engine.cache_clear()


@pytest.fixture
def db_engine():
    import core.db_models  # noqa: F401 — 모든 모델 등록

    engine = get_engine()
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(db_engine):
    from main import app

    return TestClient(app)
