"""챗봇 API (7b). 모두 환자 로그인 필요 (결정: 챗봇은 로그인한 사람만, docs/plan-step7-chat-api.md 1절 4번)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ai.agent.core.orchestrator import ChatLLM
from ai.agent.schemas import ChatResponse
from ai.agent.service import RateLimiter
from core.db import get_db
from core.security import PatientPrincipal, current_patient
from modules.chatbot import service
from modules.chatbot.schemas import AskRequest
from modules.patient.router import patient_uuid

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

Db = Annotated[Session, Depends(get_db)]
Me = Annotated[PatientPrincipal, Depends(current_patient)]
Llm = Annotated[ChatLLM, Depends(service.get_llm)]
Limiter = Annotated[RateLimiter, Depends(service.get_limiter)]


@router.post("/ask", response_model=ChatResponse)
def ask(data: AskRequest, db: Db, me: Me, llm: Llm, limiter: Limiter):
    """메시지 → 답 + 카드. session_id가 없으면 새 대화. 남의 대화 id면 404 not_found, 너무 잦으면 429 rate_limited,
    모든 LLM이 실패하면 503 chatbot.unavailable."""
    return service.ask(db, llm, limiter, patient_uuid(me), data.session_id, data.message, data.language)


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str, db: Db, me: Me) -> Response:
    """대화 삭제 버튼. 없거나 남의 대화면 404 not_found."""
    service.delete_session(db, patient_uuid(me), session_id)
    return Response(status_code=204)
