"""환율: 매일 10시(KST) 적용일 기준으로 하루 1번 받음, 주말은 직전 영업일, 실패하면 저장값, 없으면 503."""

from datetime import date, datetime, timedelta, timezone

import pytest

from modules.fx import service

KST = timezone(timedelta(hours=9))


def kst(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=KST)


@pytest.fixture
def clock(monkeypatch):
    now = {"t": kst(2026, 11, 4, 10, 30)}  # 수요일
    monkeypatch.setattr(service, "utcnow", lambda: now["t"].astimezone(timezone.utc))
    return now


@pytest.fixture
def remote(monkeypatch):
    calls = {"targets": [], "fail": False}

    def fake(target):
        calls["targets"].append(target)
        if calls["fail"]:
            raise OSError("network down")
        return {c: (0.001, target) for c in service.CURRENCIES}

    monkeypatch.setattr(service, "fetch_remote", fake)
    service.reset_failure()  # 실패 기억은 모듈 전역 → 테스트마다 비움
    yield calls
    service.reset_failure()


def get(client):
    r = client.get("/api/v1/exchange-rates")
    return r.status_code, r.json()


# --- 적용일 계산 ---


@pytest.mark.parametrize(
    "now,expected",
    [
        (kst(2026, 11, 4, 9, 59), date(2026, 11, 3)),
        (kst(2026, 11, 4, 10, 0), date(2026, 11, 4)),
        (kst(2026, 11, 4, 23, 59), date(2026, 11, 4)),
        (kst(2026, 11, 5, 0, 30), date(2026, 11, 4)),
        # UTC로는 같은 날 01:00이 한국 10:00
        (datetime(2026, 11, 4, 1, 0, tzinfo=timezone.utc), date(2026, 11, 4)),
    ],
)
def test_applied_day(now, expected):
    assert service.applied_day(now) == expected


# --- 받기 시점 ---


def test_fetches_once_per_applied_day(client, clock, remote):
    status, body = get(client)
    assert status == 200 and body["applied_on"] == "2026-11-04"
    clock["t"] = kst(2026, 11, 4, 23, 0)
    get(client)
    clock["t"] = kst(2026, 11, 5, 9, 59)  # 다음 날 10시 전 → 아직 같은 적용일
    get(client)
    assert remote["targets"] == [date(2026, 11, 4)]


def test_switches_at_10am(client, clock, remote):
    get(client)
    clock["t"] = kst(2026, 11, 5, 10, 0)
    status, body = get(client)
    assert body["applied_on"] == "2026-11-05"
    assert remote["targets"] == [date(2026, 11, 4), date(2026, 11, 5)]


def test_before_10am_first_request_uses_previous_day(client, clock, remote):
    clock["t"] = kst(2026, 11, 4, 8, 0)
    status, body = get(client)
    assert body["applied_on"] == "2026-11-03"
    assert remote["targets"] == [date(2026, 11, 3)]


def test_failure_keeps_previous_rates(client, clock, remote):
    get(client)
    clock["t"] = kst(2026, 11, 5, 10, 5)
    remote["fail"] = True
    status, body = get(client)
    assert status == 200
    assert body["applied_on"] == "2026-11-04" and body["stale"] is True


def test_after_failure_skips_refetch_for_cooldown(client, clock, remote):
    """ECOS 실패 뒤 10분은 다시 받지 않고 저장값(stale)을 바로 → 요청마다 10초 타임아웃을 기다리지 않음."""
    get(client)
    clock["t"] = kst(2026, 11, 5, 10, 5)
    remote["fail"] = True
    get(client)
    clock["t"] = kst(2026, 11, 5, 10, 14)
    status, body = get(client)
    assert status == 200 and body["stale"] is True
    assert remote["targets"] == [date(2026, 11, 4), date(2026, 11, 5)]  # 10:14에는 안 부름

    remote["fail"] = False
    clock["t"] = kst(2026, 11, 5, 10, 16)  # 10분 지남 → 다시 받음
    status, body = get(client)
    assert body["stale"] is False and body["applied_on"] == "2026-11-05"
    assert remote["targets"] == [date(2026, 11, 4), date(2026, 11, 5), date(2026, 11, 5)]


def test_first_call_race_rereads_rows_instead_of_503(client, clock, remote, monkeypatch):
    """첫 요청 둘이 동시에 받으면 늦은 쪽 저장이 PK 충돌로 실패 → 먼저 저장된 값을 다시 읽어 200."""
    from sqlalchemy.exc import IntegrityError

    real_save = service._save

    def save_after_other_request(db, fetched, target, now):
        real_save(db, fetched, target, now)  # 다른 요청이 먼저 저장했다고 치고
        raise IntegrityError("INSERT exchange_rates", None, Exception("duplicate key"))

    monkeypatch.setattr(service, "_save", save_after_other_request)
    status, body = get(client)
    assert status == 200 and body["stale"] is False and body["applied_on"] == "2026-11-04"


def test_failure_without_stored_rates_is_503(client, clock, remote):
    remote["fail"] = True
    status, body = get(client)
    assert status == 503 and body["code"] == "fx.unavailable"


def test_response_shape(client, clock, remote):
    status, body = get(client)
    assert body["base"] == "KRW"
    assert set(body["rates"]) == {"USD", "CNY", "TWD", "VND"}
    assert body["switch_hour_kst"] == 10
    assert body["provider"]["url"] == "https://ecos.bok.or.kr"


# --- ECOS 값 해석 ---


def rows(*pairs):
    return [{"TIME": t, "DATA_VALUE": v} for t, v in pairs]


def test_latest_rate_inverts_won_per_unit():
    rate, base = service.latest_rate(rows(("20261103", "1341"), ("20261104", "1,341.2")), date(2026, 11, 4), 1)
    assert base == date(2026, 11, 4)
    assert rate == pytest.approx(1 / 1341.2)


def test_latest_rate_vnd_is_per_100_dong():
    rate, _ = service.latest_rate(rows(("20261104", "5.21")), date(2026, 11, 4), 100)
    assert rate == pytest.approx(100 / 5.21)  # 1원 ≈ 19.2동


def test_latest_rate_weekend_uses_last_business_day():
    # 11/7(토)·11/8(일) 값 없음 → 11/6(금)
    rate, base = service.latest_rate(rows(("20261105", "1340"), ("20261106", "1338")), date(2026, 11, 8), 1)
    assert base == date(2026, 11, 6)


def test_latest_rate_ignores_values_after_applied_day():
    _, base = service.latest_rate(rows(("20261104", "1341"), ("20261105", "1350")), date(2026, 11, 4), 1)
    assert base == date(2026, 11, 4)


def test_fetch_requires_key(monkeypatch):
    from core.config import get_settings

    monkeypatch.setenv("ECOS_API_KEY", "")  # .env에 키가 있어도 "없음"으로
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="ECOS_API_KEY"):
        service.fetch_remote(date(2026, 11, 4))
