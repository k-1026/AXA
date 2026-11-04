import uuid
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from typing_extensions import Annotated

Lang = Literal["ko", "en", "zh-TW", "zh-CN", "vi"]


def _check_tz(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("IANA 시간대 이름이 아닙니다 (예: Asia/Taipei)")
    return value


Timezone = Annotated[str, Field(max_length=64), AfterValidator(_check_tz)]


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str | None
    preferred_lang: Lang
    timezone: str
    created_at: datetime


class PatientUpdate(BaseModel):
    """PATCH /me — 보낸 칸만 바꿈. display_name을 null로 보내면 지움(인사말은 이메일 앞부분)."""

    display_name: str | None = Field(default=None, max_length=30)
    preferred_lang: Lang | None = None
    timezone: Timezone | None = None
