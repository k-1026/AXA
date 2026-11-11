from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.db import get_db
from modules.fx import service

router = APIRouter(tags=["fx"])


class Provider(BaseModel):
    name: str
    url: str


class RatesOut(BaseModel):
    base: str
    rates: dict[str, float]  # 1 KRW = rate
    applied_on: date  # 이 환율로 안내하는 날 (매일 switch_hour_kst시에 바뀜)
    base_date: date  # 한국은행 통계 기준일 (영업일)
    switch_hour_kst: int
    stale: bool  # 갱신 실패로 예전 적용일 값인지
    provider: Provider


@router.get("/exchange-rates", response_model=RatesOut)
def exchange_rates(db: Annotated[Session, Depends(get_db)], response: Response):
    """로그인 없이. 10시 전환이 늦게 보이지 않게 브라우저 캐시는 10분만."""
    response.headers["Cache-Control"] = "public, max-age=600"
    return service.get_rates(db)
