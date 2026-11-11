"""챗봇 규칙의 백엔드 쪽 (7b). 대화 규칙 자체는 `ai/agent/service.py`의 `ChatService`가 갖고,
여기서는 계정 정보 채우기 · DB 저장소 주입 · 에러 변환만 한다.

- 환자 id·시간대는 토큰과 계정에서 (요청 본문에서 받지 않음), 언어는 요청 값 → 없으면 계정 선호 언어
- 호출 제한은 프로세스 메모리(`RateLimiter`) — 서버리스·여러 인스턴스에서는 인스턴스마다 따로 (운영 전 DB·캐시로 교체, plan-step7 3절 9번)
- `chatbot.unavailable`(503)은 계약 4절에 아직 없음 → 7c 계약 PR에서 추가
"""

from __future__ import annotations

import uuid
from functools import lru_cache

from sqlalchemy.orm import Session

from ai.agent.core.orchestrator import ChatLLM
from ai.agent.schemas import ChatResponse
from ai.agent.service import ChatService, ChatServiceError, PatientInfo, RateLimiter
from ai.llm.client import LLMClient
from core.errors import AppError
from modules.chatbot.bookings import BookingGateway
from modules.chatbot.store import DbSessionStore
from modules.patient import service as patient_service

_limiter = RateLimiter()


@lru_cache
def get_llm() -> ChatLLM:
    """FastAPI 의존성. 테스트는 app.dependency_overrides로 가짜 LLM을 넣는다."""
    return LLMClient.from_settings()


def get_limiter() -> RateLimiter:
    return _limiter


def _service(db: Session, llm: ChatLLM, limiter: RateLimiter) -> ChatService:
    return ChatService(llm, sessions=DbSessionStore(db), bookings=BookingGateway(db), limiter=limiter)


def _app_error(e: ChatServiceError) -> AppError:
    return AppError(e.status, e.code, e.message, e.detail)


def ask(db: Session, llm: ChatLLM, limiter: RateLimiter, patient_id: uuid.UUID,
        session_id: uuid.UUID | None, message: str, language: str | None) -> ChatResponse:
    patient = patient_service.get(db, patient_id)
    info = PatientInfo(str(patient_id), patient.timezone)
    try:
        return _service(db, llm, limiter).ask(info, str(session_id) if session_id else None, message,
                                              language or patient.preferred_lang)
    except ChatServiceError as e:
        raise _app_error(e) from e


def delete_session(db: Session, patient_id: uuid.UUID, session_id: str) -> None:
    """LLM·호출 제한과 무관 → 저장소만 쓴다."""
    if not DbSessionStore(db).delete(str(patient_id), session_id):
        raise AppError(404, "not_found", "대화를 찾을 수 없습니다")
