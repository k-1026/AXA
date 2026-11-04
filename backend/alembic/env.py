"""Alembic 실행 환경. DB 주소는 core.config(루트 .env의 DATABASE_URL)에서.

Supabase: 마이그레이션은 세션 풀러(포트 5432) 또는 직접 연결 주소로 실행 권장
(앱은 Vercel에서 트랜잭션 풀러 6543)
"""

from logging.config import fileConfig

from alembic import context

import core.db_models  # noqa: F401 — 모든 모델 등록
from core.db import Base, get_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):
    # 자체 타입(UTCDateTime)은 마이그레이션 파일에 기본 timestamptz로 적음
    if type_ == "type" and obj.__class__.__name__ == "UTCDateTime":
        return "sa.DateTime(timezone=True)"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=str(get_engine().url),
        target_metadata=target_metadata,
        literal_binds=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with get_engine().connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, render_item=render_item
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
