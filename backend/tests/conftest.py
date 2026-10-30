import pytest
from fastapi.testclient import TestClient

from core.config import get_settings


@pytest.fixture(autouse=True)
def test_settings(monkeypatch):
    # 테스트는 .env 값과 상관없이 고정된 가짜 비밀 키로
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-real-use-0123456789abcdef")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client():
    from main import app

    return TestClient(app)
