"""A: 방문 전 환자 질문 (결정 32) — 방문 전에만, 내 예약만, 병원 화면에 번역과 함께, 챗봇은 초안 카드만. 가상 데이터만."""

import json

import pytest
from sqlalchemy.orm import Session

from test_booking_patient import make_hospital, patient, post, slot, staff
from test_chatbot_api import ASK, call, llm, say  # noqa: F401 — llm은 fixture

API = "/api/v1"


@pytest.fixture
def db(db_engine):
    with Session(db_engine, expire_on_commit=False) as s:
        yield s


def _ask(client, rid, me, text="Can I park at the clinic?"):
    return client.post(f"{API}/me/booking-requests/{rid}/questions", json={"text": text}, headers=me)


def test_방문_전_질문은_내_예약에_쌓이고_병원_목록에도_보인다(client, db):
    h, me = make_hospital(db), patient(client)
    rid = post(client, h, me).json()["id"]
    r = _ask(client, rid, me)
    assert r.status_code == 201 and [q["text_original"] for q in r.json()["questions"]] == ["Can I park at the clinic?"]
    client.post(f"{API}/tenant/booking-requests/{rid}/confirm", json={"slot": slot(3)}, headers=staff(db, h))
    assert _ask(client, rid, me, "  What should I bring?  ").status_code == 201  # 확정 뒤에도 방문 전이면 됨
    rows = client.get(f"{API}/tenant/booking-requests", headers=staff(db, h)).json()
    assert [q["text_original"] for q in rows[0]["questions"]] == ["Can I park at the clinic?", "What should I bring?"]
    assert [q["text_original"] for q in client.get(f"{API}/me/booking-requests/{rid}", headers=me).json()["questions"]][-1] == "What should I bring?"


def test_방문_뒤나_취소된_예약은_409_남의_예약은_404_빈_글은_422(client, db):
    h, me = make_hospital(db), patient(client)
    other = patient(client, "q-other@example.com")
    rid = post(client, h, me).json()["id"]
    assert _ask(client, rid, other).status_code == 404
    assert _ask(client, rid, me, "   ").status_code == 422
    client.post(f"{API}/me/booking-requests/{rid}/cancel", json={}, headers=me)
    r = _ask(client, rid, me)
    assert (r.status_code, r.json()["code"]) == (409, "booking.invalid_transition")


def test_번역_동의가_있으면_병원용_한국어(client, db, monkeypatch):
    from modules.agent import translate

    monkeypatch.setattr(translate, "translate", lambda text, target, tenant_id=None: "주차할 수 있나요?")
    h, me = make_hospital(db), patient(client)
    rid = post(client, h, me, message="hi", consents=[{"kind": "privacy", "version": "2026-11-03"},
                                                     {"kind": "overseas_transfer", "version": "2026-11-17"}]).json()["id"]
    _ask(client, rid, me)
    q = client.get(f"{API}/tenant/booking-requests", headers=staff(db, h)).json()[0]["questions"][0]
    assert q["text_translated"] == "주차할 수 있나요?"


def test_챗봇은_초안_카드만_보내지_않음(client, db, llm):
    from modules.question.models import BookingQuestion

    h, me = make_hospital(db), patient(client)
    rid = post(client, h, me).json()["id"]
    llm.script += [call("draft_hospital_question", {"booking_id": rid, "draft": "Is there parking near the clinic?"}),
                   say("Here is a draft. Press Send if it looks right.")]
    r = client.post(ASK, headers=me, json={"message": "ask them about parking"})
    card = next(c for c in r.json()["cards"] if c["type"] == "hospital_question")["data"]
    assert card["booking_id"] == rid and card["draft"] == "Is there parking near the clinic?" and card["status"] == "draft"
    assert db.query(BookingQuestion).count() == 0  # 보내기는 환자가 카드 버튼으로


def test_챗봇_초안은_방문_뒤면_사후관리로_안내(client, db, llm):
    h, me = make_hospital(db), patient(client)
    rid = post(client, h, me).json()["id"]
    client.post(f"{API}/tenant/booking-requests/{rid}/confirm", json={"slot": slot(3)}, headers=staff(db, h))
    client.post(f"{API}/tenant/booking-requests/{rid}/visited", json={}, headers=staff(db, h))
    llm.script += [call("draft_hospital_question", {"booking_id": rid, "draft": "receipt?"}), say("Use follow-up chat.")]
    r = client.post(ASK, headers=me, json={"message": "ask about receipt"})
    assert all(c["type"] != "hospital_question" for c in r.json()["cards"])
    out = json.loads([m for m in llm.calls[-1] if m["role"] == "tool"][-1]["content"])
    assert out["status"] == "not_available" and "open_aftercare_thread" in out["reason"]
