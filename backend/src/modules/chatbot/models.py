"""챗봇 대화 저장 (결정 2·5: DB 세션, 최소 저장 — docs/plan-step7-chat-api.md, docs/backend-db-schema.md 5절).

저장하는 것: 개인정보를 가린 대화 텍스트 + 상태(체류 형태, 요청서 초안, 방금 보여 준 병원).
저장하지 않는 것: 도구 호출·결과, 카드 (화면은 그때그때 다시 만든다).

- 보관 30일 후 삭제(`sessions.purge_older_than`), 대화 삭제 버튼, 탈퇴하면 즉시 삭제 (`sessions.delete_all`)
- `state`에 요청서 초안(건강정보 포함 가능)이 있어서 제출되면 서비스 층이 지움. 개인정보보호위원회 질의 8번 회신 전 가정
- 인터페이스는 `ai/agent/session_store.py`의 `SessionStore`. DB 구현은 7b (modules/chatbot/store.py)
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base, utcnow
from modules.patient.models import LANGS

ROLES = ("user", "assistant")

# 운영(PostgreSQL)은 jsonb, 테스트(SQLite)는 JSON
JsonType = JSON().with_variant(JSONB(), "postgresql")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    lang: Mapped[str] = mapped_column(String(8))
    title: Mapped[str] = mapped_column(String(60))  # 첫 질문 앞부분(개인정보 가림). 응급이면 "[emergency message]"
    state: Mapped[dict] = mapped_column(JsonType, default=dict, server_default=text("'{}'"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_message_at: Mapped[datetime] = mapped_column(default=utcnow)

    __table_args__ = (
        CheckConstraint("lang IN (" + ", ".join(f"'{x}'" for x in LANGS) + ")", name="lang"),
        Index("ix_chat_sessions_patient", "patient_id", "last_message_at"),  # 내 대화 목록(최근 순)·개수 제한
        Index("ix_chat_sessions_last_message", "last_message_at"),  # 30일 지난 대화 정리
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    # bigint identity (SQLite 테스트에서는 INTEGER PRIMARY KEY)
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer(), "sqlite"), Identity(), primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(9))
    content: Mapped[str] = mapped_column(Text)  # 개인정보를 가린 텍스트
    refused: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))  # 거절·차단이 있었던 턴
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    __table_args__ = (
        CheckConstraint("role IN (" + ", ".join(f"'{x}'" for x in ROLES) + ")", name="role"),
        Index("ix_chat_messages_session", "session_id", "id"),
    )
