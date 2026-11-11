"""챗봇 대화 테이블 (chat_sessions, chat_messages): 제약, 상태 JSON, 탈퇴 즉시 삭제, 30일 정리.
이메일·비밀번호·대화 내용은 가상 값만."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.db import utcnow
from modules.chatbot import sessions as chat_sessions
from modules.chatbot.models import ChatMessage, ChatSession
from modules.patient.models import Patient

from test_auth_patient import auth, signup, withdraw


def make_patient(db: Session, email="chat1@example.com") -> Patient:
    p = Patient(email=email, password_hash="x", age14_confirmed_at=utcnow())
    db.add(p)
    db.commit()
    return p


def make_session(db: Session, patient: Patient, title="hello", **kw) -> ChatSession:
    s = ChatSession(patient_id=patient.id, lang="en", title=title, **kw)
    db.add(s)
    db.commit()
    return s


def add_messages(db: Session, session: ChatSession, n=2) -> None:
    for i in range(n):
        db.add(ChatMessage(session_id=session.id, role="user" if i % 2 == 0 else "assistant", content=f"m{i}"))
    db.commit()


def count(db: Session, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_state_json_round_trips_and_defaults(db_engine):
    with Session(db_engine, expire_on_commit=False) as db:
        p = make_patient(db)
        plain = make_session(db, p)
        assert plain.state == {}  # 기본값
        state = {"residency": "short_term", "draft": {"hospital_id": 9002, "preferred_slots": ["2026-12-04 10:00"]},
                 "shown_hospitals": [{"id": 9002, "name": "Demo Dermatology Clinic B"}]}
        rich = make_session(db, p, state=state)
        db.expire_all()
        assert db.get(ChatSession, rich.id).state == state
        assert db.get(ChatSession, rich.id).created_at.tzinfo is not None  # UTC 시간대가 붙은 값


def test_messages_get_increasing_ids_and_defaults(db_engine):
    with Session(db_engine) as db:
        s = make_session(db, make_patient(db))
        add_messages(db, s, 3)
        rows = db.scalars(select(ChatMessage).where(ChatMessage.session_id == s.id).order_by(ChatMessage.id)).all()
        assert [r.content for r in rows] == ["m0", "m1", "m2"] and rows[0].id < rows[1].id < rows[2].id
        assert rows[0].refused is False and rows[0].created_at.tzinfo is not None


@pytest.mark.parametrize("lang", ["ja", "zh", ""])
def test_session_lang_must_be_one_of_the_ui_languages(db_engine, lang):
    with Session(db_engine) as db:
        p = make_patient(db)
        db.add(ChatSession(patient_id=p.id, lang=lang, title="t"))
        with pytest.raises(IntegrityError):
            db.commit()


def test_message_role_must_be_user_or_assistant(db_engine):
    with Session(db_engine) as db:
        s = make_session(db, make_patient(db))
        db.add(ChatMessage(session_id=s.id, role="system", content="x"))
        with pytest.raises(IntegrityError):
            db.commit()


def test_delete_all_removes_only_that_patients_chats(db_engine):
    with Session(db_engine) as db:
        mine, other = make_patient(db), make_patient(db, "chat2@example.com")
        for p, n in ((mine, 2), (other, 1)):
            for _ in range(n):
                add_messages(db, make_session(db, p), 2)
        assert chat_sessions.delete_all(db, mine.id) == 2
        db.commit()
        assert db.scalars(select(ChatSession.patient_id)).all() == [other.id]
        assert count(db, ChatMessage) == 2  # 남의 메시지는 그대로, 내 메시지는 메시지부터 지워짐
        assert chat_sessions.delete_all(db, uuid.uuid4()) == 0


def test_purge_older_than_keeps_recent_sessions(db_engine):
    with Session(db_engine) as db:
        p = make_patient(db)
        old = make_session(db, p, title="old")
        new = make_session(db, p, title="new")
        old.last_message_at = utcnow() - timedelta(days=35)
        db.commit()
        add_messages(db, old, 2)
        add_messages(db, new, 2)
        assert chat_sessions.purge_older_than(db, utcnow() - timedelta(days=30)) == 1
        db.commit()
        assert [s.title for s in db.scalars(select(ChatSession)).all()] == ["new"]
        assert count(db, ChatMessage) == 2


def test_withdraw_deletes_chats_immediately_but_not_other_patients(client, db_engine):
    token = signup(client)
    other = signup(client, email="patient2@example.com")
    with Session(db_engine) as db:
        mine_id = db.scalar(select(Patient.id).where(Patient.email == "patient1@example.com"))
        other_id = db.scalar(select(Patient.id).where(Patient.email == "patient2@example.com"))
        for pid in (mine_id, mine_id, other_id):
            add_messages(db, make_session(db, db.get(Patient, pid), state={"draft": {"hospital_id": 1}}), 2)
        assert count(db, ChatSession) == 3 and count(db, ChatMessage) == 6
    assert withdraw(client, token).status_code == 204
    with Session(db_engine) as db:
        assert db.scalars(select(ChatSession.patient_id)).all() == [other_id]  # 내 대화 2개는 사라짐
        assert count(db, ChatMessage) == 2
    assert client.get("/api/v1/me", headers=auth(other)).status_code == 200


def test_wrong_password_withdrawal_keeps_chats(client, db_engine):
    token = signup(client)
    with Session(db_engine) as db:
        pid = db.scalar(select(Patient.id))
        add_messages(db, make_session(db, db.get(Patient, pid)), 2)
    assert withdraw(client, token, "wrong-password-99").status_code == 401
    with Session(db_engine) as db:
        assert count(db, ChatSession) == 1 and count(db, ChatMessage) == 2
