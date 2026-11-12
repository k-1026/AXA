"""정기 정리 (보관 기간): 30일 지난 챗봇 대화 + 만료·로그아웃한 로그인 세션 삭제.

POST(·GET) /api/v1/internal/purge가 부른다. 예약 작업(Vercel Cron 등)이 하루 1번 불러야 함 — 부르지 않으면 지워지지 않음.
"""

from datetime import timedelta

from sqlalchemy.orm import Session

from ai.agent.service import RETENTION_DAYS
from core.db import utcnow
from modules.auth import sessions as auth_sessions
from modules.chatbot import sessions as chat_sessions


def purge(db: Session) -> dict[str, int]:
    """한 번에 commit. 지운 행 수 (대화 = 세션 수)."""
    chats = chat_sessions.purge_older_than(db, utcnow() - timedelta(days=RETENTION_DAYS))
    dead = auth_sessions.purge_dead(db)
    db.commit()
    return {"chat_sessions": chats, "auth_sessions": dead}
