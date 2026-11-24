"""B 모듈 agent(A 작성): 메시지 번역 — 동의가 있을 때만, 개인정보 가림, 실패해도 보내기는 됨 (결정 25). 실제 LLM은 부르지 않음."""

import uuid
from dataclasses import dataclass

import pytest
from sqlalchemy.orm import Session

from core.security import create_access_token
from db_rows import demo_staff
from modules.aftercare import service as aftercare
from modules.agent import translate
from modules.booking import service as booking
from modules.consent.models import Consent

from test_aftercare_tenant import _patient, _req, _tenant


@dataclass
class _Res:
    text: str


class FakeLLM:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def chat(self, messages, **kw):
        self.calls.append(messages)
        if self.fail:
            raise RuntimeError("down")
        lang = messages[0]["content"].split("into ")[1].split(".")[0]
        return _Res(f"[{lang}] {messages[1]['content']}")


@pytest.fixture
def db(db_engine):
    with Session(db_engine, expire_on_commit=False) as s:
        yield s


@pytest.fixture
def llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(translate, "_llm", lambda: fake)
    return fake


def _consent(db, p, r):
    db.add(Consent(patient_id=p.id, kind="overseas_transfer", version="2026-11-18", lang="zh-TW", booking_request_id=r.id))
    db.commit()


def test_사후관리_환자글은_한국어로_직원글은_환자언어로(client, db, llm):
    p, t = _patient(db), _tenant(db)
    r = _req(db, p, t)
    _consent(db, p, r)
    thread = aftercare.patient_open(db, p.id, r.id, "臉還是紅的，email me at a@b.com")
    staff = demo_staff(db, t.id)
    aftercare.tenant_reply(db, t.id, str(staff.id), thread.id, "사진을 보내 주세요")
    _, _, msgs = aftercare.tenant_messages(db, t.id, thread.id)
    assert msgs[0].text_translated == "[Korean] 臉還是紅的，email me at [email]"  # 개인정보 가림
    assert msgs[1].text_translated == "[Traditional Chinese (Taiwan)] 사진을 보내 주세요"
    assert all("a@b.com" not in m[1]["content"] for m in llm.calls)


def test_동의가_없으면_LLM을_부르지_않고_원문만(db, llm):
    p, t = _patient(db), _tenant(db)
    r = _req(db, p, t)
    aftercare.patient_open(db, p.id, r.id, "臉還是紅的")
    assert llm.calls == []


def test_상담_답장도_환자_언어로(db, llm):
    p, t = _patient(db), _tenant(db)
    r = _req(db, p, t, visited=False)
    _consent(db, p, r)
    reply = booking.staff_reply(db, t.id, str(uuid.uuid4()), r.id, "다음 주 화요일 가능해요")
    assert reply.text_translated == "[Traditional Chinese (Taiwan)] 다음 주 화요일 가능해요"


def test_번역이_실패해도_보내기는_된다(client, db, monkeypatch):
    monkeypatch.setattr(translate, "_llm", lambda: FakeLLM(fail=True))
    p, t = _patient(db), _tenant(db)
    r = _req(db, p, t)
    _consent(db, p, r)
    thread = aftercare.patient_open(db, p.id, r.id, "臉還是紅的")
    _, _, msgs = aftercare.tenant_messages(db, t.id, thread.id)
    assert msgs[0].text_original == "臉還是紅的" and msgs[0].text_translated is None


def test_사진만_한국어끼리는_번역하지_않음(llm):
    assert translate.translate("📷", "ko") is None
    assert translate.translate("hello", "xx") is None
    assert llm.calls == []
