"""챗봇 대화 행의 일괄 삭제 (탈퇴·보관 기간 정리). commit하지 않는다 — 호출하는 쪽이 한다.

DB의 FK CASCADE에 기대지 않고 메시지부터 직접 지운다: SQLite 테스트에서도 같게 동작하게 (auth/sessions.py와 같은 방식).
"""

import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from modules.chatbot.models import ChatMessage, ChatSession


def delete_all(db: Session, patient_id: uuid.UUID) -> int:
    """탈퇴할 때 그 환자의 대화 전부 삭제. 지운 세션 수."""
    ids = select(ChatSession.id).where(ChatSession.patient_id == patient_id)
    db.execute(delete(ChatMessage).where(ChatMessage.session_id.in_(ids)))
    return db.execute(delete(ChatSession).where(ChatSession.patient_id == patient_id)).rowcount


def purge_older_than(db: Session, cutoff: datetime) -> int:
    """마지막 대화가 cutoff보다 오래된 세션 삭제 (보관 30일 정리, 매일 cron). 지운 세션 수."""
    ids = select(ChatSession.id).where(ChatSession.last_message_at < cutoff)
    db.execute(delete(ChatMessage).where(ChatMessage.session_id.in_(ids)))
    return db.execute(delete(ChatSession).where(ChatSession.last_message_at < cutoff)).rowcount
