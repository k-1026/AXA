from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.db import get_db
from modules.pageview import service

router = APIRouter(tags=["hospitals"])


class PageViewIn(BaseModel):
    hospital: str = Field(min_length=1, max_length=200, description="병원 ykiho (화면의 병원 id)")
    visitor_key: str = Field(pattern=r"^[A-Za-z0-9_-]{16,64}$", description="브라우저 무작위 값, 하루마다 바뀜")
    lang: Literal["ko", "en", "zh-TW", "zh-CN", "vi", "ja"] | None = None


@router.post("/hospitals/page-views", status_code=204)
def record_page_view(body: PageViewIn, db: Annotated[Session, Depends(get_db)]) -> Response:
    """로그인 없이. 병원 상세 페이지를 열면 1번 (같은 방문자·같은 날은 한 번만 셈). 개인정보 저장 안 함."""
    service.record_view(db, body.hospital, body.visitor_key, body.lang)
    return Response(status_code=204)
