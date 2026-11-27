"""이미 있는 환자 계정 1개에 시연용 예약·사후관리 가상 데이터를 넣는다. 여러 번 돌려도 같은 결과.

    uv run --no-sync python backend/scripts/seed_account_demo.py --email <환자 이메일>
    uv run --no-sync python backend/scripts/seed_account_demo.py --email <환자 이메일> --dry-run

- 가상 병원(9001~9004, `seed_demo_shared.py`가 만든 tenant)에만 넣음 — 실제 병원은 건드리지 않음 (compliance 2-6)
- 다시 돌리면 이 환자의 예약·사후관리를 지우고 새로 만듦
- 넣는 것: 방문 완료 2건(사후관리 진행 중 1 · 해결 1) · 확정 1건 · 대기 1건 · 취소 1건
- 실명·실제 환자 정보 없음. 메시지는 미리 쓴 한국어 가상 문장 (LLM 안 부름)
- 요청서 국적·상담 언어는 외국인 단기 방문자로 (11/27): 대만·베트남·일본·미국·중국을 요청마다 돌아가며.
  한국 국적·한국어는 넣지 않음 (전에는 국적 KR·언어=계정 언어(ko)라 병원 요청 목록에 "한국·한국어"가 보였음, 결정 36)
"""

import argparse
import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))
sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import core.db_models  # noqa: E402,F401
from core.db import get_engine  # noqa: E402
from modules.aftercare.models import AftercareMessage, AftercareThread  # noqa: E402
from modules.booking.models import BookingEvent, BookingRequest  # noqa: E402
from modules.consent.models import Consent  # noqa: E402
from modules.consent.service import CURRENT_VERSIONS  # noqa: E402
from modules.patient.models import Patient  # noqa: E402
from modules.tenant.models import StaffUser, Tenant  # noqa: E402

KST = ZoneInfo("Asia/Seoul")
# (국적, 상담 언어) — 요청마다 차례로. 한국 국적·한국어는 넣지 않음 (결정 36: 한국 국적은 유치 대상 아님)
VISITORS = [("TW", "zh-TW"), ("VN", "vi"), ("JP", "ja"), ("US", "en"), ("CN", "zh-CN")]
_visitor = iter(())


def next_visitor() -> tuple[str, str]:
    global _visitor
    try:
        return next(_visitor)
    except StopIteration:
        _visitor = iter(VISITORS)
        return next(_visitor)


def kst(d, h: int, m: int = 0) -> datetime:
    return datetime.combine(d, time(h, m), KST).astimezone(timezone.utc)


def clear(db: Session, p: Patient) -> None:
    ids = list(db.scalars(select(BookingRequest.id).where(BookingRequest.patient_id == p.id)))
    if not ids:
        return
    tids = list(db.scalars(select(AftercareThread.id).where(AftercareThread.request_id.in_(ids))))
    if tids:
        db.execute(delete(AftercareMessage).where(AftercareMessage.thread_id.in_(tids)))
        db.execute(delete(AftercareThread).where(AftercareThread.id.in_(tids)))
    db.execute(delete(BookingEvent).where(BookingEvent.request_id.in_(ids)))
    db.execute(delete(Consent).where(Consent.booking_request_id.in_(ids)))
    db.execute(delete(BookingRequest).where(BookingRequest.id.in_(ids)))
    db.flush()


def add_booking(db: Session, p: Patient, t: Tenant, status: str, created: datetime, slot: datetime | None,
                treatment: str, msg: str, path: list[tuple[str, datetime, str]], reason: str | None = None) -> BookingRequest:
    nationality, lang = next_visitor()
    req = BookingRequest(
        patient_id=p.id, tenant_id=t.id, hospital_id=t.hospital_id, status=status, lang=lang,
        nationality=nationality, contact_method="email", department_code="dermatology", treatment=treatment, visa_needed=False,
        preferred_slots=[(slot or created + timedelta(days=5)).isoformat()], message_original=msg,
        patient_timezone=p.timezone or "Asia/Seoul", confirmed_slot=slot if status in ("confirmed", "visited") else None,
        created_at=created, updated_at=path[-1][1] if path else created,
    )
    db.add(req)
    db.flush()
    db.add(Consent(patient_id=p.id, booking_request_id=req.id, kind="privacy", version=CURRENT_VERSIONS["privacy"],
                   lang=req.lang, agreed_at=created))
    db.add(BookingEvent(request_id=req.id, from_status=None, to_status="pending", actor_type="patient", created_at=created))
    prev = "pending"
    for nxt, at, actor in path:
        db.add(BookingEvent(request_id=req.id, from_status=prev, to_status=nxt, actor_type=actor, created_at=at,
                            reason=reason if nxt == "cancelled" else None))
        prev = nxt
    db.flush()
    return req


def add_thread(db: Session, req: BookingRequest, t: Tenant, staff_id, status: str, tags: list[str],
               msgs: list[tuple[str, str, datetime]]) -> None:
    th = AftercareThread(request_id=req.id, tenant_id=t.id, status=status, tags=tags, created_at=msgs[0][2],
                         last_message_at=msgs[-1][2], resolved_at=msgs[-1][2] if status == "resolved" else None)
    db.add(th)
    db.flush()
    for sender, text, at in msgs:
        db.add(AftercareMessage(thread_id=th.id, sender=sender, staff_id=staff_id if sender == "staff" else None,
                                text_original=text, attachments=[], created_at=at))
    db.flush()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    now = datetime.now(timezone.utc)
    today = now.astimezone(KST).date()
    d = lambda n: today + timedelta(days=n)  # noqa: E731
    with Session(get_engine()) as db:
        p = db.scalar(select(Patient).where(Patient.email == args.email))
        if p is None:
            sys.exit(f"환자 계정 없음: {args.email}")
        tenants = {t.hospital_id: t for t in db.scalars(select(Tenant).where(Tenant.hospital_id.in_([9001, 9002, 9003, 9004])))}
        if len(tenants) < 4:
            sys.exit("가상 병원 tenant가 없음 → 먼저 seed_demo_shared.py 실행")
        staff = {hid: db.scalar(select(StaffUser.id).where(StaffUser.tenant_id == t.id).limit(1)) for hid, t in tenants.items()}
        clear(db, p)

        # 1) 9001 방문 완료 → 사후관리 진행 중 (환자 마지막 메시지에 아직 답 없음)
        c = kst(d(-14), 10)
        slot = kst(d(-8), 11)
        r = add_booking(db, p, tenants[9001], "visited", c, slot, "laser_toning", "레이저 토닝 상담 받고 싶어요. 몇 번 받아야 하나요?",
                        [("confirmed", c + timedelta(hours=3), "staff"), ("visited", slot + timedelta(hours=1), "staff")])
        add_thread(db, r, tenants[9001], staff[9001], "in_progress", ["redness"], [
            ("patient", "시술 다음 날인데 볼 쪽이 아직 조금 붉어요. 괜찮은 건가요?", kst(d(-7), 9, 20)),
            ("staff", "시술 후 1~3일 정도 붉은 기는 흔합니다. 진정 크림을 바르시고 뜨거운 사우나는 피해 주세요.", kst(d(-7), 10, 5)),
            ("patient", "감사합니다. 많이 가라앉았어요. 2회차는 언제쯤 받으면 될까요?", kst(d(-2), 20, 40)),
        ])

        # 2) 9002 방문 완료 → 사후관리 해결됨
        c = kst(d(-30), 14)
        slot = kst(d(-24), 15)
        r = add_booking(db, p, tenants[9002], "visited", c, slot, "acne_scar", "여드름 흉터 치료 문의드립니다.",
                        [("confirmed", c + timedelta(hours=5), "staff"), ("visited", slot + timedelta(hours=1), "staff")])
        add_thread(db, r, tenants[9002], staff[9002], "resolved", ["scab"], [
            ("patient", "딱지가 생겼는데 떼어도 되나요?", kst(d(-22), 11)),
            ("staff", "자연스럽게 떨어질 때까지 두세요. 억지로 떼면 자국이 남을 수 있습니다.", kst(d(-22), 13, 30)),
            ("patient", "네, 알겠습니다. 이제 다 떨어졌어요!", kst(d(-17), 18)),
            ("staff", "경과가 좋네요. 불편한 점 있으면 언제든 말씀 주세요.", kst(d(-17), 18, 45)),
        ])

        # 3) 9003 확정 (다가오는 상담)
        c = kst(d(-2), 16)
        slot = kst(d(3), 14, 30)
        add_booking(db, p, tenants[9003], "confirmed", c, slot, "botox", "사각턱 보톡스 상담 예약하고 싶습니다.",
                    [("confirmed", c + timedelta(hours=2), "staff")])

        # 4) 9004 대기 (병원 답 기다리는 중)
        c = kst(d(0), 9, 30) if now.astimezone(KST).hour >= 10 else kst(d(-1), 19)
        add_booking(db, p, tenants[9004], "pending", c, kst(d(6), 11), "melasma", "기미 치료 가능한 날짜 알려 주세요.", [])

        # 5) 9003 취소 (예전 일정)
        c = kst(d(-40), 11)
        add_booking(db, p, tenants[9003], "cancelled", c, kst(d(-35), 10), "filler", "필러 상담 문의",
                    [("confirmed", c + timedelta(hours=4), "staff"), ("cancelled", c + timedelta(days=2), "patient")],
                    reason="schedule")

        if args.dry_run:
            db.rollback()
        else:
            db.commit()
    print(f"{args.email}: 예약 5건 · 사후관리 2건", "(dry-run, 저장 안 함)" if args.dry_run else "저장함")


if __name__ == "__main__":
    main()
