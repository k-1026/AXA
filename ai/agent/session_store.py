"""챗봇 대화 저장소 (결정 2·5: DB 세션, 최소 저장).

이 파일에는 **인터페이스와 메모리 구현**만 있다. 백엔드(7b)가 같은 인터페이스로 DB 구현(`chat_sessions`,
`chat_messages`)을 만들어 주입한다 — `ChatService`는 어느 쪽인지 모른다.

저장하는 것: 개인정보를 가린 대화 텍스트 + 상태(체류 형태, 요청서 초안, 보여 준 병원). 도구 호출·결과·카드는 저장하지 않는다.
모든 읽기·삭제는 `patient_id`로 범위를 좁힌다 → 남의 세션은 "없음"과 같게 보인다(계약 4절 `not_found`).
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

JSON = dict[str, Any]


@dataclass
class StoredSession:
    id: str
    patient_id: str
    lang: str
    title: str  # 첫 질문 앞부분(개인정보 가림), 마이페이지 "지난 대화" 목록용
    state: JSON
    created_at: datetime
    last_message_at: datetime


@dataclass
class StoredMessage:
    role: str  # "user" | "assistant"
    content: str  # 개인정보를 가린 텍스트
    refused: bool = False  # 거절·차단이 있었던 턴
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SessionStore(Protocol):
    def create(self, patient_id: str, lang: str, title: str, state: JSON) -> StoredSession: ...

    def get(self, patient_id: str, session_id: str) -> StoredSession | None:
        """내 세션만. 없거나 남의 것이면 None."""

    def messages(self, session_id: str, limit: int) -> list[StoredMessage]:
        """오래된 것부터, 최근 limit개."""

    def append(self, session_id: str, messages: list[StoredMessage], state: JSON) -> None:
        """메시지를 붙이고 상태를 바꾸고 last_message_at을 갱신 (한 번에)."""

    def delete(self, patient_id: str, session_id: str) -> bool: ...

    def count(self, patient_id: str) -> int: ...

    def purge_older_than(self, cutoff: datetime) -> int:
        """마지막 대화가 cutoff보다 오래된 세션을 지우고 개수를 돌려준다 (보관 기간 정리 작업용)."""


class InMemorySessionStore:
    """테스트·시연용. 서버가 다시 켜지면 사라지고, 여러 인스턴스가 공유하지 못한다 → 운영에서는 DB 구현."""

    def __init__(self, clock: Callable[[], datetime] | None = None):
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._sessions: dict[str, StoredSession] = {}
        self._messages: dict[str, list[StoredMessage]] = {}

    def create(self, patient_id: str, lang: str, title: str, state: JSON) -> StoredSession:
        now = self._clock()
        s = StoredSession(str(uuid.uuid4()), patient_id, lang, title, copy.deepcopy(state), now, now)
        self._sessions[s.id] = s
        self._messages[s.id] = []
        return copy.deepcopy(s)

    def get(self, patient_id: str, session_id: str) -> StoredSession | None:
        s = self._sessions.get(session_id)
        return copy.deepcopy(s) if s and s.patient_id == patient_id else None

    def messages(self, session_id: str, limit: int) -> list[StoredMessage]:
        return copy.deepcopy(self._messages.get(session_id, [])[-limit:])

    def append(self, session_id: str, messages: list[StoredMessage], state: JSON) -> None:
        s = self._sessions[session_id]
        self._messages[session_id].extend(copy.deepcopy(messages))
        s.state = copy.deepcopy(state)
        s.last_message_at = self._clock()

    def delete(self, patient_id: str, session_id: str) -> bool:
        s = self._sessions.get(session_id)
        if not s or s.patient_id != patient_id:
            return False
        del self._sessions[session_id]
        del self._messages[session_id]
        return True

    def count(self, patient_id: str) -> int:
        return sum(1 for s in self._sessions.values() if s.patient_id == patient_id)

    def purge_older_than(self, cutoff: datetime) -> int:
        old = [sid for sid, s in self._sessions.items() if s.last_message_at < cutoff]
        for sid in old:
            del self._sessions[sid]
            del self._messages[sid]
        return len(old)

    def delete_all_for_patient(self, patient_id: str) -> int:
        """탈퇴 때 즉시 삭제 (DB에서는 FK CASCADE가 하는 일)."""
        mine = [sid for sid, s in self._sessions.items() if s.patient_id == patient_id]
        for sid in mine:
            del self._sessions[sid]
            del self._messages[sid]
        return len(mine)
