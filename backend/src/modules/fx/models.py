"""환율 (가격 가이드 통화 표시용). 1원 = rate 통화 단위. 매일 오전 10시(한국 시간) 기준으로 하루 1번."""

from datetime import date, datetime

from sqlalchemy import Date, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    currency: Mapped[str] = mapped_column(String(3), primary_key=True)  # USD, CNY, TWD, VND
    rate: Mapped[float] = mapped_column(Float)  # 1 KRW = rate currency
    base_date: Mapped[date] = mapped_column(Date)  # 한국은행 통계의 날짜 (영업일)
    applied_on: Mapped[date] = mapped_column(Date)  # 이 값을 안내하는 날 (10시 기준)
    fetched_at: Mapped[datetime]  # 받아 온 시각
