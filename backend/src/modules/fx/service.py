"""환율: 매일 오전 10시(한국 시간)에 그날 적용 환율을 정하고, 다음 날 10시 전까지 같은 값으로 안내.

- 출처: 한국은행 경제통계시스템(ECOS) 731Y001 「주요국통화의 대원화환율」(일별)
  원/미국달러·원/위안은 매매기준율, 원/베트남동은 100동당 → 1원당 외화로 뒤집어 저장
- "적용일" = 한국 시간 10시 이후면 오늘, 10시 전이면 어제
  저장된 값의 적용일이 지금 적용일과 다르면 그때 ECOS에서 받아 옴 (서버리스라 예약 작업 없이도 정확히 10시에 바뀜)
  Vercel 예약 작업(cron)은 미리 받아 두는 용도로만 (무료 플랜은 ±59분 어긋남)
- 받을 때는 적용일까지(포함) 최근 영업일 값을 씀 → 주말·공휴일은 직전 영업일 값
- 받기에 실패하면 저장된 값(stale), 저장된 값도 없으면 503 fx.unavailable
- 가격 표시는 참고용 환산 (실제 비용은 원화, 병원 안내 기준)
"""

import json
import logging
import urllib.request
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import get_settings
from core.db import utcnow
from core.errors import AppError
from modules.fx.models import ExchangeRate

log = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))
PROVIDER = {"name": "한국은행 경제통계시스템(ECOS)", "url": "https://ecos.bok.or.kr"}
STAT_CODE = "731Y001"
# 통화 → (ECOS 항목 코드, 원화 표시 단위). 베트남동은 "100동당 원"
ITEMS = {
    "USD": ("0000001", 1),
    "CNY": ("0000053", 1),
    "TWD": ("0000031", 1),
    "VND": ("0000035", 100),
}
CURRENCIES = tuple(ITEMS)  # 프론트 통화 선택과 같게 (KRW는 기준)
LOOKBACK_DAYS = 10  # 긴 연휴도 덮도록


def applied_day(now: datetime) -> date:
    kst = now.astimezone(KST)
    hour = get_settings().fx_switch_hour_kst
    return kst.date() if kst.hour >= hour else kst.date() - timedelta(days=1)


def _ecos_rows(key: str, item: str, start: date, end: date) -> list[dict]:
    url = (
        f"https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/{LOOKBACK_DAYS + 5}/"
        f"{STAT_CODE}/D/{start:%Y%m%d}/{end:%Y%m%d}/{item}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "axa-backend"})
    with urllib.request.urlopen(req, timeout=10) as res:  # URL에 키가 있어 로그에 남기지 않음
        data = json.load(res)
    if "StatisticSearch" not in data:
        raise RuntimeError(f"ECOS 응답 오류: {data.get('RESULT', {}).get('CODE')}")
    return data["StatisticSearch"]["row"]


def latest_rate(rows: list[dict], until: date, unit: int) -> tuple[float, date]:
    """until(포함)까지 가장 최근 값 → (1원당 외화, 기준일)."""
    usable = [r for r in rows if r.get("DATA_VALUE") and datetime.strptime(r["TIME"], "%Y%m%d").date() <= until]
    if not usable:
        raise RuntimeError("ECOS에 기간 안 값이 없음")
    last = max(usable, key=lambda r: r["TIME"])
    won_per_unit = float(last["DATA_VALUE"].replace(",", ""))
    return unit / won_per_unit, datetime.strptime(last["TIME"], "%Y%m%d").date()


def fetch_remote(target: date) -> dict[str, tuple[float, date]]:
    """ECOS에서 적용일까지의 최근 값. 테스트에서 바꿔 끼움."""
    key = get_settings().ecos_api_key
    if not key:
        raise RuntimeError("ECOS_API_KEY가 없음 (.env)")
    start = target - timedelta(days=LOOKBACK_DAYS)
    return {
        cur: latest_rate(_ecos_rows(key, item, start, target), target, unit)
        for cur, (item, unit) in ITEMS.items()
    }


def get_rates(db: Session) -> dict:
    rows = {r.currency: r for r in db.scalars(select(ExchangeRate))}
    now = utcnow()
    target = applied_day(now)
    current = len(rows) == len(CURRENCIES) and all(r.applied_on == target for r in rows.values())
    if not current:
        try:
            fetched = fetch_remote(target)
            for cur, (rate, base) in fetched.items():
                db.merge(ExchangeRate(currency=cur, rate=rate, base_date=base, applied_on=target, fetched_at=now))
            db.commit()
            rows = {r.currency: r for r in db.scalars(select(ExchangeRate))}
        except Exception as e:  # 네트워크·ECOS 오류 → 저장된 값으로
            db.rollback()
            log.error("환율 갱신 실패: %s", type(e).__name__)
            if not rows:
                raise AppError(503, "fx.unavailable", "환율 정보를 가져올 수 없습니다")

    return {
        "base": "KRW",
        "rates": {c: rows[c].rate for c in CURRENCIES if c in rows},
        "applied_on": min(r.applied_on for r in rows.values()),
        "base_date": min(r.base_date for r in rows.values()),
        "switch_hour_kst": get_settings().fx_switch_hour_kst,
        "stale": any(r.applied_on != target for r in rows.values()),
        "provider": PROVIDER,
    }
