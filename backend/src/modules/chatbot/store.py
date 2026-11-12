"""`SessionStore`의 DB 구현 (7b). 인터페이스는 `ai/agent/session_store.py`.

- 모든 읽기·삭제는 `patient_id`로 범위를 좁힌다 → 남의 세션은 "없음"(계약 4절 `not_found`)
- 쓰기는 메서드마다 commit (요청 하나에 세션 하나라서 다른 작업과 섞이지 않음).
  단 `create`는 commit하지 않음 → 바로 뒤 첫 `append`와 한 번에 (저장 실패 시 빈 세션이 남지 않게)
- 같은 대화에 동시에 두 요청이 오면 `state`는 늦게 저장한 쪽 것이 남음 (낙관적 잠금 없음, 팀 확인)
- id가 uuid 형식이 아니면 "없음"으로 본다 (잘못된 경로 값으로 500이 나지 않게)
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ai.agent.session_store import JSON, StoredMessage, StoredSession
from core.db import utcnow
from modules.chatbot import sessions as bulk
from modules.chatbot.models import ChatMessage, ChatSession


def _uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _out(s: ChatSession) -> StoredSession:
    return StoredSession(
        id=str(s.id), patient_id=str(s.patient_id), lang=s.lang, title=s.title, state=dict(s.state or {}),
        created_at=s.created_at, last_message_at=s.last_message_at,
    )


class DbSessionStore:
    def __init__(self, db: Session):
        self.db = db

    def _row(self, patient_id: str, session_id: str) -> ChatSession | None:
        pid, sid = _uuid(patient_id), _uuid(session_id)
        if pid is None or sid is None:
            return None
        return self.db.scalar(select(ChatSession).where(ChatSession.id == sid, ChatSession.patient_id == pid))

    def create(self, patient_id: str, lang: str, title: str, state: JSON) -> StoredSession:
        now = utcnow()
        s = ChatSession(patient_id=uuid.UUID(patient_id), lang=lang, title=title[:60], state=dict(state),
                        created_at=now, last_message_at=now)
        self.db.add(s)
        self.db.flush()  # id만 받음. commit은 첫 append에서
        return _out(s)

    def get(self, patient_id: str, session_id: str) -> StoredSession | None:
        s = self._row(patient_id, session_id)
        return _out(s) if s else None

    def messages(self, session_id: str, limit: int) -> list[StoredMessage]:
        sid = _uuid(session_id)
        if sid is None:
            return []
        rows = self.db.scalars(
            select(ChatMessage).where(ChatMessage.session_id == sid).order_by(ChatMessage.id.desc()).limit(limit)
        ).all()
        return [StoredMessage(m.role, m.content, m.refused, m.created_at) for m in reversed(rows)]

    def append(self, session_id: str, messages: list[StoredMessage], state: JSON) -> None:
        s = self.db.get(ChatSession, uuid.UUID(session_id))
        if s is None:  # 같은 순간에 삭제됨 → 저장하지 않는다
            return
        for m in messages:
            self.db.add(ChatMessage(session_id=s.id, role=m.role, content=m.content, refused=m.refused,
                                    created_at=m.created_at))
        s.state = dict(state)  # 새 dict를 넣어야 JSON 칸 변경이 반영됨
        s.last_message_at = utcnow()
        self.db.commit()

    def delete(self, patient_id: str, session_id: str) -> bool:
        s = self._row(patient_id, session_id)
        if s is None:
            return False
        self.db.query(ChatMessage).filter(ChatMessage.session_id == s.id).delete()
        self.db.delete(s)
        self.db.commit()
        return True

    def count(self, patient_id: str) -> int:
        pid = _uuid(patient_id)
        if pid is None:
            return 0
        return self.db.scalar(select(func.count()).select_from(ChatSession).where(ChatSession.patient_id == pid)) or 0

    def purge_older_than(self, cutoff: datetime) -> int:
        n = bulk.purge_older_than(self.db, cutoff)
        self.db.commit()
        return n
