"""챗봇 서비스 층 — 백엔드 라우터가 부르는 유일한 입구 (7a, docs/plan-step7-chat-api.md).

    service = ChatService(llm, sessions=<SessionStore>, bookings=<BookingGateway>)
    response = service.ask(PatientInfo("…", "Asia/Taipei"), session_id, "message", "en")

FastAPI·DB에 의존하지 않는다 → 이 PC에서도 테스트된다. 백엔드는 인증(`current_patient`)·DB 구현·에러 변환만 한다.

맡는 일
- 호출 제한(계정당), 입력 검사(길이·언어 코드), 세션 소유 확인(남의 세션 = not_found)
- 저장된 텍스트 대화 + 상태로 오케스트레이터 맥락을 다시 만든다 (도구 결과는 저장하지 않으므로 "방금 보여 준 병원" 등을 상태에서 복원)
- **제출 확인**: 요청서는 사람이 쓰는 것과 같은 API로 제출된다(결정 3). 다음 대화에서 "초안의 병원에 초안 이후 생긴 내 요청이
  있는지"를 게이트웨이로 확인해 초안을 비우고 모델에게 알린다 (서버 기록이 기준, 어느 화면에서 제출했든 동일)
- 응답 카드를 Pydantic 모델로 검증 (형식이 어긋나면 그 카드만 뺀다)
- 모든 LLM 제공자가 실패하면 `chatbot.unavailable`(503). 제공자 오류 원문은 밖으로 내지 않는다
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Protocol

from pydantic import ValidationError

from ai.agent.core.orchestrator import ChatLLM, ChatReply, ConversationState, Orchestrator
from ai.agent.schemas import CARD_ADAPTER, UI_LANGUAGES, ChatResponse
from ai.agent.session_store import JSON, SessionStore, StoredMessage, StoredSession
from ai.agent.tools.chat_tools import build_registry
from ai.agent.tools.registry import ToolRegistry
from ai.llm import safety
from ai.llm.retry import LLMError

log = logging.getLogger(__name__)

RETENTION_DAYS = 30  # docs/backend-db-schema.md 제안. 법적 기준은 미확인
MAX_SESSIONS_PER_PATIENT = 50
MAX_MESSAGE_CHARS = 1000
HISTORY_MESSAGES = 20  # 모델에게 주는 최근 텍스트 메시지 수
SHOWN_HOSPITALS_KEPT = 10
LANGUAGE_ALIASES = {"zh": "zh-CN", "zh-Hans": "zh-CN", "zh-hans": "zh-CN", "zh-Hant": "zh-TW", "zh-hant": "zh-TW",
                    "zh-cn": "zh-CN", "zh-tw": "zh-TW"}


class ChatServiceError(Exception):
    """백엔드가 `AppError(status, code, message, detail)`로 그대로 바꾼다. 코드는 docs/backend-contracts.md 4절."""

    def __init__(self, status: int, code: str, message: str, detail: JSON | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.detail = status, code, message, detail or {}


@dataclass(frozen=True)
class PatientInfo:
    """토큰과 계정에서 라우터가 채운다. 요청 본문에서 받지 않는다."""

    patient_id: str
    timezone: str = "UTC"  # patients.timezone


class BookingGateway(Protocol):
    """도구와 제출 확인이 쓰는 예약 조회. 지금은 `BookingStore`(가짜), 7b에서 `booking.service` 어댑터로 교체.
    get_for_patient는 없거나 남의 것이면 `BookingError("not_found")`를 낸다."""

    def list_for_patient(self, patient_id: str, status: str | None = None) -> list[JSON]: ...

    def get_for_patient(self, patient_id: str, booking_id: str) -> JSON: ...


class RateLimiter:
    """계정당 분·일 상한 (메모리). 서버리스·다중 인스턴스에서는 인스턴스마다 따로라서 운영에서는 DB·캐시 기반으로 바꾼다.
    기본값은 무료 키 한도를 아끼기 위한 가정이다."""

    def __init__(self, per_minute: int = 10, per_day: int = 150):
        self.per_minute, self.per_day = per_minute, per_day
        self._hits: dict[str, deque[datetime]] = defaultdict(deque)

    def check(self, key: str, now: datetime) -> None:
        hits = self._hits[key]
        while hits and now - hits[0] > timedelta(days=1):
            hits.popleft()
        minute = [t for t in hits if now - t <= timedelta(minutes=1)]
        if len(minute) >= self.per_minute:
            wait = int((minute[0] + timedelta(minutes=1) - now).total_seconds()) + 1
            raise ChatServiceError(429, "rate_limited", "요청이 너무 많습니다", {"retry_after": wait, "limit": "minute"})
        if len(hits) >= self.per_day:
            wait = int((hits[0] + timedelta(days=1) - now).total_seconds()) + 1
            raise ChatServiceError(429, "rate_limited", "오늘 사용 한도를 넘었습니다", {"retry_after": wait, "limit": "day"})
        hits.append(now)


def normalize_language(code: str) -> str:
    code = LANGUAGE_ALIASES.get(code, code)
    if code not in UI_LANGUAGES:
        raise ChatServiceError(422, "validation", "지원하지 않는 언어입니다", {"language": code, "supported": list(UI_LANGUAGES)})
    return code


def _shown_from_cards(cards: list[JSON]) -> list[JSON] | None:
    """이번 턴에 보여 준 병원 목록(표시 순서). 목록·추천 카드가 있으면 그것으로 갈아 끼운다."""
    for card in reversed(cards):
        if card["type"] == "hospital_list":
            return [{"id": h["hospital_id"], "name": h["name_en"]} for h in card["data"]["hospitals"]]
        if card["type"] == "hospital_suggestions":
            return [{"id": h["hospital_id"], "name": h["name_en"]} for h in card["data"]["suggestions"]]
        if card["type"] == "hospital_detail":
            d = card["data"]
            return [{"id": d["hospital_id"], "name": d["name_en"]}]
    return None


def build_context(state: JSON, submitted: JSON | None) -> str | None:
    """저장된 상태에서 모델용 맥락을 만든다. 사용자가 쓴 자유 문장(문의 내용·건강정보)은 넣지 않는다 —
    신뢰하는 시스템 영역에 사용자 글이 섞이지 않게 (그 글은 대화 기록에서 이미 보인다)."""
    lines: list[str] = []
    if state.get("shown_hospitals"):
        listed = "; ".join(f"{i}. {h['name']} (id {h['id']})" for i, h in enumerate(state["shown_hospitals"], 1))
        lines.append(f"Hospitals most recently shown to the user, in display order: {listed}. When the user says \"the first one\" "
                     "or \"that clinic\", use these ids; never ask the user for an id.")
    d = state.get("draft")
    if d:
        lines.append(
            "Open request draft (NOT submitted yet): "
            f"hospital {d.get('hospital_name_en')} (id {d.get('hospital_id')}), department {d.get('department')}, "
            f"preferred slots {d.get('preferred_slots')}, language {d.get('language')}, nationality {d.get('nationality')}, "
            f"visa help {d.get('visa_needed')}. If the user changes any detail, call prepare_booking_request again with ALL fields."
        )
    if submitted:
        lines.append(
            f"The patient submitted the request to {submitted.get('hospital_name_en')} (id {submitted.get('id')}, status "
            f"{submitted.get('status')}) since the last message. Say it was sent and the hospital will confirm, decline, or propose "
            "another time; the status can be checked here. The draft is closed."
        )
    if lines:
        lines.append("Earlier tool results are not in the chat history; call the tools again if you need facts.")
    return "\n".join(f"- {x}" for x in lines) if lines else None


class ChatService:
    def __init__(
        self,
        llm: ChatLLM,
        *,
        sessions: SessionStore,
        bookings: BookingGateway,
        registry: ToolRegistry | None = None,
        limiter: RateLimiter | None = None,
        clock: Callable[[], datetime] | None = None,
        safety_check: Callable[[str, str], safety.SafetyResult] | None = safety.check,
    ):
        self.sessions = sessions
        self.bookings = bookings
        self.limiter = limiter or RateLimiter()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.orchestrator = Orchestrator(
            llm, registry or build_registry(), store=bookings, safety_check=safety_check, today=lambda: self._clock().date()
        )

    # ------------------------------------------------------------------ 대화
    def ask(self, patient: PatientInfo, session_id: str | None, message: str, language: str) -> ChatResponse:
        message = (message or "").strip()
        if not message:
            raise ChatServiceError(422, "validation", "메시지가 비어 있습니다")
        if len(message) > MAX_MESSAGE_CHARS:
            raise ChatServiceError(422, "validation", "메시지가 너무 깁니다", {"max_chars": MAX_MESSAGE_CHARS})
        language = normalize_language(language)
        self.limiter.check(patient.patient_id, self._clock())

        session: StoredSession | None = None
        if session_id is not None:
            session = self.sessions.get(patient.patient_id, session_id)
            if session is None:
                raise ChatServiceError(404, "not_found", "대화를 찾을 수 없습니다")
        elif self.sessions.count(patient.patient_id) >= MAX_SESSIONS_PER_PATIENT:
            raise ChatServiceError(429, "rate_limited", "저장된 대화가 너무 많습니다. 지난 대화를 지워 주세요",
                                   {"limit": "sessions", "max": MAX_SESSIONS_PER_PATIENT})

        saved: JSON = dict(session.state) if session else {}
        history = [{"role": m.role, "content": m.content} for m in self.sessions.messages(session.id, HISTORY_MESSAGES)] if session else []

        # 제출 확인: 초안의 병원에 초안 이후 생긴 내 요청이 있으면 제출된 것
        submitted = None
        draft = saved.get("draft")
        if draft:
            known = set(saved.get("draft_known_booking_ids", []))
            fresh = [b for b in self.bookings.list_for_patient(patient.patient_id)
                     if b["hospital_id"] == draft["hospital_id"] and b["id"] not in known]
            if fresh:
                submitted = fresh[-1]
                draft = None
                saved.pop("draft", None)
                saved.pop("draft_known_booking_ids", None)

        state = ConversationState(
            language=language, patient_id=patient.patient_id, residency=saved.get("residency"),
            history=history, booking_draft=draft, timezone=patient.timezone,
        )
        try:
            reply: ChatReply = self.orchestrator.handle(state, message, extra_context=build_context(saved | {"draft": draft}, submitted))
        except LLMError as e:
            log.warning("chat LLM failure: %s", type(e).__name__)  # 제공자 오류 원문은 로그에도 남기지 않는다(입력이 섞일 수 있음)
            raise ChatServiceError(503, "chatbot.unavailable", "지금은 챗봇을 사용할 수 없습니다. 잠시 뒤 다시 시도해 주세요") from e

        cards = self._validated_cards(reply)

        # ---- 저장할 상태
        new_state: JSON = {k: v for k, v in saved.items() if k in ("shown_hospitals",)}
        if state.residency:
            new_state["residency"] = state.residency
        if state.booking_draft:
            new_state["draft"] = state.booking_draft
            if any(c.type == "booking_draft" for c in cards):  # 새 초안: 이 시점의 내 요청 id를 기억
                new_state["draft_known_booking_ids"] = [b["id"] for b in self.bookings.list_for_patient(patient.patient_id)]
            else:
                new_state["draft_known_booking_ids"] = saved.get("draft_known_booking_ids", [])
        shown = _shown_from_cards([c.model_dump(mode="json") for c in cards])
        if shown:
            new_state["shown_hospitals"] = shown[:SHOWN_HOSPITALS_KEPT]

        # ---- 저장 (개인정보를 가린 텍스트만)
        if session is None:
            title = "[emergency message]" if reply.blocked else safety.mask_pii(message)[0][:60]
            session = self.sessions.create(patient.patient_id, language, title, new_state)
        refused = reply.blocked or bool(reply.safety_categories)
        now = self._clock()
        self.sessions.append(
            session.id,
            [StoredMessage("user", reply.user_text, refused, now), StoredMessage("assistant", reply.text, refused, now)],
            new_state,
        )
        return ChatResponse(
            session_id=session.id, text=reply.text, cards=cards, ai_generated=reply.ai_generated,
            blocked=reply.blocked, medical_notice=reply.medical_notice,
        )

    def delete_session(self, patient: PatientInfo, session_id: str) -> None:
        if not self.sessions.delete(patient.patient_id, session_id):
            raise ChatServiceError(404, "not_found", "대화를 찾을 수 없습니다")

    def purge_expired(self) -> int:
        """보관 기간(30일)이 지난 대화 삭제. 백엔드의 정기 작업이 부른다."""
        return self.sessions.purge_older_than(self._clock() - timedelta(days=RETENTION_DAYS))

    # ------------------------------------------------------------------ 내부
    @staticmethod
    def _validated_cards(reply: ChatReply) -> list[Any]:
        out = []
        for card in reply.cards:
            try:
                out.append(CARD_ADAPTER.validate_python(card))
            except ValidationError as e:  # 도구 결과와 카드 모델이 어긋남 → 그 카드만 뺀다 (테스트가 잡아야 하는 버그)
                log.error("card dropped: %s %s", card.get("type"), e.errors()[:1])
        return out
