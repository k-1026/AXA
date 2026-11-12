import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ConsentKind = Literal["terms", "privacy", "health", "overseas_transfer"]


class ConsentIn(BaseModel):
    kind: ConsentKind
    version: str = Field(min_length=1, max_length=16)  # 동의 문구 버전 (프론트가 보여준 것)


class ConsentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: ConsentKind
    version: str
    lang: str
    booking_request_id: uuid.UUID | None
    agreed_at: datetime
    withdrawn_at: datetime | None
