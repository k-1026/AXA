import pytest
from fastapi.testclient import TestClient

from core.config import get_settings
from core.db import Base, get_engine


@pytest.fixture(autouse=True)
def test_settings(monkeypatch):
    # 테스트는 .env 값과 상관없이 고정된 가짜 비밀 키 + 메모리 DB로
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-real-use-0123456789abcdef")
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    # .env에 Supabase 키가 있어도 테스트는 실제 Storage를 부르지 않음 (필요한 테스트만 가짜로 켬)
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "")
    # 웹 푸시도 .env 키와 상관없이 꺼 둠 (푸시 테스트만 가짜 키로 켬, 결정 30)
    monkeypatch.setenv("VAPID_PUBLIC_KEY", "")
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "")
    # 실제 병원 입점 신청도 .env와 상관없이 기본(닫힘)으로 (여는 테스트만 켬)
    monkeypatch.setenv("STAFF_SIGNUP_REAL_HOSPITALS", "false")
    get_settings.cache_clear()
    get_engine.cache_clear()
    # 번역은 실제 LLM을 부르지 않음 (번역을 보는 테스트만 가짜 LLM으로 바꿈)
    from modules.agent import translate

    monkeypatch.setattr(translate, "_llm", lambda: None)
    from modules.auth import attempts

    attempts.reset_all()  # 로그인 시도 기록은 모듈 전역 → 테스트마다 비움
    yield
    get_settings.cache_clear()
    get_engine.cache_clear()


@pytest.fixture
def db_engine():
    import core.db_models  # noqa: F401 — 모든 모델 등록

    engine = get_engine()
    # SQLite는 FK를 기본으로 검사하지 않음 → Postgres(Supabase)처럼 없는 병원·요청서 id를 막게
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys = ON")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(db_engine):
    from main import app

    return TestClient(app)
