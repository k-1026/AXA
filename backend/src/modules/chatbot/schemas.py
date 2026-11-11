"""챗봇 API 입력. 응답은 `ai.agent.schemas.ChatResponse`(카드 모델 포함)를 그대로 쓴다 → OpenAPI → shared-types."""

import uuid

from pydantic import BaseModel, Field

from ai.agent.service import MAX_MESSAGE_CHARS


class AskRequest(BaseModel):
    session_id: uuid.UUID | None = None  # 없으면 새 대화
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    # 비우면 계정의 선호 언어. ko, en, zh-TW, zh-CN, vi (zh·zh-Hans·zh-Hant 같은 별칭은 서비스가 정리)
    language: str | None = Field(default=None, max_length=16)
