"""B 모듈(A 작성): 직원이 요청서·사후관리를 열람·답장하면 열람 기록이 남고, 자기 병원 기록만 본다. 가상 데이터만."""

import uuid

from sqlalchemy.orm import Session
import pytest

from core.security import create_access_token
from modules.aftercare import service as aftercare
from modules.audit import service as audit
from modules.audit.models import AuditLog

from db_rows import demo_staff
from test_aftercare_tenant import _patient, _req, _tenant


@pytest.fixture
def db(db_engine):
    with Session(db_engine, expire_on_commit=False) as s:
        yield s


def _h(t, sid):
    return {"Authorization": f"Bearer {create_access_token(sid, 'staff', tenant_id=str(t.id))}"}


def test_열람_답장마다_기록되고_내용은_남기지_않는다(client, db):
    p, t = _patient(db), _tenant(db)
    sid = str(demo_staff(db, t.id).id)  # 사후관리 답장의 staff_id FK → 실제 직원 행
    r = _req(db, p, t)
    thread = aftercare.patient_open(db, p.id, r.id, "얼굴이 빨개요")

    client.get("/api/v1/tenant/booking-requests", headers=_h(t, sid))
    client.get(f"/api/v1/tenant/booking-requests/{r.id}", headers=_h(t, sid))
    client.post(f"/api/v1/tenant/booking-requests/{r.id}/replies", json={"text": "확인했어요"}, headers=_h(t, sid))
    client.get(f"/api/v1/tenant/aftercare/{thread.id}", headers=_h(t, sid))
    client.post(f"/api/v1/tenant/aftercare/{thread.id}/messages", json={"text": "사진 보내 주세요"}, headers=_h(t, sid))

    logs = client.get("/api/v1/tenant/audit-logs", headers=_h(t, sid)).json()
    assert [x["action"] for x in logs] == ["aftercare.reply", "aftercare.view", "booking.reply", "booking.view", "booking.list"]
    assert {x["actor"] for x in logs} == {sid}
    assert logs[1]["ref"] == f"aftercare_thread:{thread.id}" and logs[4]["ref"] == "booking_requests:1"
    assert not any("빨개요" in x["ref"] or "사진" in x["ref"] for x in logs)  # 내용 없음


def test_다른_병원_기록은_안_보이고_남의_대화를_열려_하면_기록도_없다(client, db):
    p, a, b = _patient(db), _tenant(db, 9001), _tenant(db, 9002)
    thread = aftercare.patient_open(db, p.id, _req(db, p, a).id, "질문")
    client.get(f"/api/v1/tenant/aftercare/{thread.id}", headers=_h(a, "s-a"))
    assert client.get(f"/api/v1/tenant/aftercare/{thread.id}", headers=_h(b, "s-b")).status_code == 404
    assert client.get("/api/v1/tenant/audit-logs", headers=_h(b, "s-b")).json() == []
    assert db.query(AuditLog).count() == 1


def test_모르는_행동은_기록하지_않는다(db):
    t = _tenant(db)
    with pytest.raises(ValueError):
        audit.log_action(db, t.id, "s", "patient.export", "x")


def test_환자_토큰으로는_기록을_볼_수_없다(client):
    tok = create_access_token(str(uuid.uuid4()), "patient", session_id="s")
    assert client.get("/api/v1/tenant/audit-logs", headers={"Authorization": f"Bearer {tok}"}).status_code == 403
