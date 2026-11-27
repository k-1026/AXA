"""병원 상세 페이지 조회 기록 (page_events) → 대시보드 "상세페이지 방문자" (11/27)"""

import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.security import create_access_token
from db_rows import demo_hospital
from modules.booking import analytics
from modules.pageview import service
from modules.pageview.models import PageEvent
from modules.tenant.models import Tenant

KEY_A = "a" * 32
KEY_B = "b" * 32


@pytest.fixture
def db(db_engine):
    with Session(db_engine, expire_on_commit=False) as s:
        yield s


def _tenant(db: Session, hospital_id: int) -> Tenant:
    demo_hospital(db, hospital_id)
    t = Tenant(hospital_id=hospital_id, display_name=f"가상 {hospital_id}", requests_enabled=True, registration_no="DEMO-0001")
    db.add(t)
    db.commit()
    return t


def test_same_visitor_same_day_counts_once(db):
    demo_hospital(db, 9001)
    day = date(2026, 11, 27)
    assert service.record_view(db, "DEMO-9001", KEY_A, "ja", today=day) is True
    assert service.record_view(db, "DEMO-9001", KEY_A, "ja", today=day) is False  # 새로고침
    assert service.record_view(db, "DEMO-9001", KEY_B, None, today=day) is True  # 다른 방문자
    assert service.record_view(db, "DEMO-9001", KEY_A, "ja", today=date(2026, 11, 28)) is True  # 다음 날
    assert service.count_views(db, 9001, day, day) == 2
    assert service.count_views(db, 9001, day, date(2026, 11, 28)) == 3


def test_no_personal_data_columns():
    cols = {c.name for c in PageEvent.__table__.columns}
    assert cols == {"id", "hospital_id", "type", "visitor_key", "day", "lang", "created_at"}  # 환자 id·IP·기기 없음


def test_api_records_without_login_and_validates(client, db):
    demo_hospital(db, 9001)
    db.commit()
    ok = client.post("/api/v1/hospitals/page-views", json={"hospital": "DEMO-9001", "visitor_key": KEY_A, "lang": "vi"})
    assert ok.status_code == 204
    again = client.post("/api/v1/hospitals/page-views", json={"hospital": "DEMO-9001", "visitor_key": KEY_A})
    assert again.status_code == 204
    assert db.scalar(select(PageEvent.lang).where(PageEvent.visitor_key == KEY_A)) == "vi"
    assert len(db.scalars(select(PageEvent)).all()) == 1
    assert client.post("/api/v1/hospitals/page-views", json={"hospital": "NOPE", "visitor_key": KEY_A}).status_code == 404
    for bad in ({"hospital": "DEMO-9001", "visitor_key": "short"}, {"hospital": "DEMO-9001", "visitor_key": "x" * 20 + "!"}):
        assert client.post("/api/v1/hospitals/page-views", json=bad).status_code == 422


def test_dashboard_views_are_my_hospital_only_with_prev_period(client, db):
    t, _other = _tenant(db, 9001), _tenant(db, 9002)
    for i, d in enumerate([date(2026, 11, 2), date(2026, 11, 2), date(2026, 11, 20)]):
        service.record_view(db, "DEMO-9001", f"{i:032d}", None, today=d)
    service.record_view(db, "DEMO-9001", KEY_A, None, today=date(2026, 10, 20))  # 지난 기간 (10/16~10/31)
    service.record_view(db, "DEMO-9002", KEY_B, None, today=date(2026, 11, 2))  # 다른 병원

    s = analytics.summary(db, t.id, date(2026, 11, 1), date(2026, 11, 16), today=date(2026, 11, 16))
    views = next(k for k in s["kpi"] if k["key"] == "views")
    assert (views["now"], views["prev"]) == (2, 1)
    assert "views" not in s["suppressed"]

    series = analytics.series(db, t.id, date(2026, 11, 1), date(2026, 11, 27))
    assert sum(b["now"]["views"] for b in series["buckets"]) == 3
    assert series["buckets"][0]["now"]["views"] == 2  # 11/1~11/3

    token = create_access_token(str(uuid.uuid4()), "staff", tenant_id=str(t.id))
    body = client.get("/api/v1/tenant/analytics/summary?from=2026-11-01&to=2026-11-27", headers={"Authorization": f"Bearer {token}"}).json()
    assert next(k for k in body["kpi"] if k["key"] == "views")["now"] == 3
