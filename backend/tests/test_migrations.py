"""마이그레이션 = 모델: 빈 DB에 `alembic upgrade head`를 한 결과가 SQLAlchemy 모델과 같아야 한다.

테이블·칸·FK가 빠지거나 남으면 실패 (B가 모델을 바꾸면 A가 리비전을 만들어야 함, AGENTS.md 4절).
SQLite로 확인하므로 타입·CHECK·서버 기본값 차이는 보지 않는다 (Postgres 전용 차이는 Supabase 적용 때 확인).
"""

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

from core.config import get_settings
from core.db import Base, get_engine


def _config() -> Config:
    """alembic.ini를 읽지 않는 설정 → env.py가 logging fileConfig를 하지 않음 (다른 테스트의 로그 캡처를 끄지 않게)."""
    cfg = Config()
    cfg.set_main_option("script_location", "backend/alembic")
    return cfg


STRUCTURAL = {"add_table", "remove_table", "add_column", "remove_column", "add_fk", "remove_fk"}


def _kinds(diffs):
    out = []
    for d in diffs:
        if isinstance(d, list):  # modify_* 묶음
            out += _kinds(d)
        elif d[0] in STRUCTURAL:
            obj = d[1] if d[0] in ("add_table", "remove_table") else d[-1]
            out.append((d[0], getattr(obj, "name", str(obj))))
    return out


@pytest.fixture
def migrated_url(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'm.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    get_engine.cache_clear()
    command.upgrade(_config(), "head")
    return url


def test_빈_DB에_upgrade_head를_하면_모델과_구조가_같다(migrated_url):
    import core.db_models  # noqa: F401 — 모든 모델 등록

    engine = create_engine(migrated_url)
    with engine.connect() as conn:
        diffs = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert _kinds(diffs) == []


def test_downgrade_0006_후_다시_upgrade(migrated_url):
    cfg = _config()
    command.downgrade(cfg, "0006")
    command.upgrade(cfg, "head")
