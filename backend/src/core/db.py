"""DB 연결 (SQLAlchemy 2, 동기). 운영 = Supabase PostgreSQL, 테스트 = 메모리 SQLite.

- Vercel 서버리스는 요청마다 함수가 뜨고 꺼지므로 연결 풀을 들고 있지 않음(NullPool)
- Supabase 트랜잭션 풀러(포트 6543)는 prepared statement를 지원하지 않음 → psycopg에서 끔
- 시간은 UTC(timestamptz)로만 저장 (결정 4). 시간대 없는 datetime은 저장 거부
"""

from collections.abc import Iterator
from datetime import datetime, timezone
from functools import lru_cache

from sqlalchemy import DateTime, Engine, MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.pool import NullPool, StaticPool
from sqlalchemy.types import TypeDecorator

from core.config import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """timestamptz. 저장할 때 UTC로 바꾸고, 읽을 때 항상 시간대가 붙은 값으로 돌려준다."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("시간대 없는 datetime은 저장하지 않습니다 (UTC로 넘길 것)")
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is not None and value.tzinfo is None:  # SQLite는 시간대를 버림
            value = value.replace(tzinfo=timezone.utc)
        return value


# 제약 조건 이름 규칙 → Alembic 자동 생성 시 이름이 일정하게
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)
    type_annotation_map = {datetime: UTCDateTime()}


def normalize_db_url(url: str) -> str:
    """Supabase에서 복사한 주소를 그대로 넣어도 되게. 드라이버는 psycopg 3."""
    url = url.strip()
    if url.startswith("http"):
        raise RuntimeError(
            "DATABASE_URL에 Supabase 프로젝트 주소(https://…supabase.co)가 들어 있음. "
            "Supabase > Connect > Connection string의 postgresql://… 주소를 넣을 것"
        )
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def make_engine(url: str) -> Engine:
    url = normalize_db_url(url)
    if url.startswith("sqlite") and ":memory:" in url:
        # 테스트: 메모리 DB를 여러 요청이 같이 쓰도록 연결 하나만
        return create_engine(url, poolclass=StaticPool, connect_args={"check_same_thread": False})
    if url.startswith("postgresql"):
        return create_engine(url, poolclass=NullPool, connect_args={"prepare_threshold": None})
    return create_engine(url)


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL이 없습니다 (.env에 Supabase 연결 문자열)")
    return make_engine(url)


def get_db() -> Iterator[Session]:
    """FastAPI 의존성. 요청 하나에 세션 하나, commit은 service에서."""
    with Session(get_engine(), expire_on_commit=False) as session:
        yield session
