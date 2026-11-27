"""요청부터 결제까지 단계별 시연 데이터: 가상 환자 몇 명이 각자 다른 단계에 있게 넣는다. 여러 번 돌려도 같은 결과.

    uv run --no-sync python backend/scripts/seed_flow_demo.py              # 가상 병원 9001
    uv run --no-sync python backend/scripts/seed_flow_demo.py --hospital 9002 --dry-run
    uv run --no-sync python backend/scripts/seed_flow_demo.py --remove     # 이 스크립트가 넣은 환자·예약만 지움

실제 흐름 순서 그대로 (상태 이력 booking_events도 같은 순서·시각):
  요청(pending) → 병원 시간 제안(proposed) → 확정(confirmed) → 방문 완료(visited) → 결제 확인(paid)
| 환자 | 단계 | 병원 대시보드에서 보이는 곳 |
|---|---|---|
| flow-demo-1 Mei | 요청만 보냄 (확인 대기) + 방문 전 질문 | 상담·예약 → 대기 |
| flow-demo-2 Minh | 병원이 다른 시간 제안, 환자 답 기다림 | 시간 제안함 |
| flow-demo-3 Yuki | 확정 (사흘 뒤 방문) + 병원 답장 | 이번 주 확정·달력 |
| flow-demo-4 Emily | 방문 완료, 결제 금액 입력 전 | 진료·결제 확인 → 입력 대기 |
| flow-demo-5 Li | 결제 확인 ₩730,000 카드 | 진료·결제 확인 → 확인 완료 |
| flow-demo-6 Chen | 결제 확인 ₩1,860,000 현금 + 사후관리 대화 | 확인 완료 · 사후관리 |

- 가상 병원(9001~9004, `seed_demo_shared.py`가 만든 tenant)에만 — 실제 병원은 건드리지 않음 (compliance 2-6)
- 가상 환자: `flow-demo-<n>@example.com`, 로그인 불가 비밀번호(해시 아님), 국적·언어는 외국인 단기 방문자(KR·ko 없음, 결정 36)
- 다시 돌리면 이 환자들을 지우고 새로 만듦 (예약·이력·질문·답장·사후관리도 같이)
- 실명·실제 환자 정보 없음. 글·번역은 미리 쓴 가상 문장 (LLM 안 부름) — 환자 글에는 한국어 번역을 같이 넣어 대시보드에 "번역 전"이 안 보이게
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
from modules.booking.models import BookingEvent, BookingRequest, Reply  # noqa: E402
from modules.consent.models import Consent  # noqa: E402
from modules.consent.service import CURRENT_VERSIONS  # noqa: E402
from modules.notification.models import Notification, StaffNotification  # noqa: E402
from modules.patient.models import Patient  # noqa: E402
from modules.question.models import BookingQuestion  # noqa: E402
from modules.tenant.models import StaffUser, Tenant  # noqa: E402

KST = ZoneInfo("Asia/Seoul")
EMAIL = "flow-demo-{n}@example.com"
NO_LOGIN = "!flow-demo-no-login"  # argon2 해시가 아니라 어떤 비밀번호로도 로그인 안 됨
# 환자 글의 한국어 번역 (병원 대시보드는 번역을 같이 보여 줌 — 비우면 "번역 전"으로 보임). 미리 쓴 가상 번역, LLM 안 부름
KO = {
    "想做雷射淨膚，請問需要做幾次？": "레이저 토닝을 받고 싶어요. 몇 번 받아야 하나요?",
    "Tôi muốn điều trị nám, ngày nào còn chỗ?": "기미 치료를 받고 싶어요. 어느 날짜에 자리가 있나요?",
    "エラボトックスの相談を予約したいです。": "사각턱 보톡스 상담을 예약하고 싶어요.",
    "I'd like a consultation for acne scars.": "여드름 흉터 상담을 받고 싶어요.",
    "想预约激光嫩肤。": "레이저 토닝을 예약하고 싶어요.",
    "想治療肝斑，大概要幾次？": "기미 치료를 받고 싶어요. 대략 몇 번 받아야 하나요?",
    "治療後臉有點紅，正常嗎？": "치료 뒤 얼굴이 조금 붉어요. 정상인가요?",
    "好多了，謝謝！下次什麼時候可以再做？": "많이 좋아졌어요, 감사합니다! 다음에는 언제 다시 받을 수 있나요?",
}
# 병원(한국어) 글의 환자 언어 번역 — 사후관리 대화
TW = {"시술 뒤 2~3일 붉은 기는 흔합니다. 진정 크림을 바르고 뜨거운 곳은 피해 주세요.": "術後2~3天泛紅很常見。請擦鎮靜霜，並避免高溫場所。"}


def kst(d, h: int, m: int = 0) -> datetime:
    return datetime.combine(d, time(h, m), KST).astimezone(timezone.utc)


def remove(db: Session) -> int:
    pids = list(db.scalars(select(Patient.id).where(Patient.email.like("flow-demo-%@example.com"))))
    if not pids:
        return 0
    rids = list(db.scalars(select(BookingRequest.id).where(BookingRequest.patient_id.in_(pids))))
    if rids:
        tids = list(db.scalars(select(AftercareThread.id).where(AftercareThread.request_id.in_(rids))))
        if tids:
            db.execute(delete(AftercareMessage).where(AftercareMessage.thread_id.in_(tids)))
            db.execute(delete(AftercareThread).where(AftercareThread.id.in_(tids)))
        for model in (BookingEvent, BookingQuestion, Reply, Notification, StaffNotification):
            db.execute(delete(model).where(model.request_id.in_(rids)))
        db.execute(delete(Consent).where(Consent.booking_request_id.in_(rids)))
        db.execute(delete(BookingRequest).where(BookingRequest.id.in_(rids)))
    db.execute(delete(Consent).where(Consent.patient_id.in_(pids)))
    db.execute(delete(Patient).where(Patient.id.in_(pids)))
    db.flush()
    return len(pids)


def patient(db: Session, n: int, name: str, lang: str, country: str, tz: str, joined: datetime) -> Patient:
    p = Patient(email=EMAIL.format(n=n), password_hash=NO_LOGIN, display_name=f"{name} (예시)", preferred_lang=lang,
                timezone=tz, age14_confirmed_at=joined, residency="short_term", residence_country=country,
                residency_answered_at=joined, created_at=joined, updated_at=joined)
    db.add(p)
    db.flush()
    return p


def booking(db: Session, p: Patient, t: Tenant, nationality: str, created: datetime, wish: datetime, treatment: str,
            msg: str, path: list[tuple[str, datetime, str, datetime | None]], paid: tuple[int, str] | None = None) -> BookingRequest:
    """path: (다음 상태, 시각, 누가, 그때 정한 시간). 마지막 상태가 지금 상태"""
    status = path[-1][0] if path else "pending"
    slot = next((s for _, _, _, s in reversed(path) if s is not None), None)
    req = BookingRequest(
        patient_id=p.id, tenant_id=t.id, hospital_id=t.hospital_id, status=status, lang=p.preferred_lang,
        nationality=nationality, contact_method="email", department_code="dermatology", treatment=treatment,
        visa_needed=False, preferred_slots=[wish.isoformat()], message_original=msg, message_translated=KO.get(msg),
        patient_timezone=p.timezone,
        confirmed_slot=slot, paid_amount=paid[0] if paid else None, paid_method=paid[1] if paid else None,
        created_at=created, updated_at=path[-1][1] if path else created,
    )
    db.add(req)
    db.flush()
    db.add(Consent(patient_id=p.id, booking_request_id=req.id, kind="privacy", version=CURRENT_VERSIONS["privacy"],
                   lang=req.lang, agreed_at=created))
    db.add(BookingEvent(request_id=req.id, from_status=None, to_status="pending", actor_type="patient", created_at=created))
    prev = "pending"
    for nxt, at, actor, s in path:
        db.add(BookingEvent(request_id=req.id, from_status=prev, to_status=nxt, actor_type=actor, created_at=at,
                            proposed_slot=s))
        prev = nxt
    db.flush()
    return req


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hospital", type=int, default=9001, choices=[9001, 9002, 9003, 9004])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--remove", action="store_true", help="넣은 것만 지우고 끝")
    args = ap.parse_args()
    today = datetime.now(KST).date()
    d = lambda n: today + timedelta(days=n)  # noqa: E731
    with Session(get_engine()) as db:
        t = db.scalar(select(Tenant).where(Tenant.hospital_id == args.hospital))
        if t is None:
            sys.exit("가상 병원 tenant가 없음 → 먼저 seed_demo_shared.py 실행")
        staff_id = db.scalar(select(StaffUser.id).where(StaffUser.tenant_id == t.id).limit(1))
        removed = remove(db)
        if args.remove:
            db.rollback() if args.dry_run else db.commit()
            print(f"지움: 가상 환자 {removed}명")
            return

        # 1) 요청만 보냄 (오늘) + 방문 전 질문
        p = patient(db, 1, "Mei", "zh-TW", "TW", "Asia/Taipei", kst(d(-1), 21))
        c = kst(d(0), 8, 40)
        r = booking(db, p, t, "TW", c, kst(d(5), 11), "laser_toning", "想做雷射淨膚，請問需要做幾次？", [])
        db.add(BookingQuestion(request_id=r.id, text_original="當天可以刷卡嗎？", text_translated="당일 카드 결제가 되나요?",
                               created_at=c + timedelta(minutes=5)))

        # 2) 병원이 다른 시간 제안 → 환자 답 기다림
        p = patient(db, 2, "Minh", "vi", "VN", "Asia/Ho_Chi_Minh", kst(d(-4), 10))
        c = kst(d(-3), 10, 15)
        booking(db, p, t, "VN", c, kst(d(4), 10), "melasma", "Tôi muốn điều trị nám, ngày nào còn chỗ?",
                [("proposed", c + timedelta(hours=4), "staff", kst(d(4), 15))])

        # 3) 확정 (사흘 뒤 방문) + 병원 답장
        p = patient(db, 3, "Yuki", "ja", "JP", "Asia/Tokyo", kst(d(-6), 19))
        c = kst(d(-5), 20, 10)
        r = booking(db, p, t, "JP", c, kst(d(3), 14), "botox", "エラボトックスの相談を予約したいです。",
                    [("confirmed", c + timedelta(hours=14), "staff", kst(d(3), 14))])
        db.add(Reply(request_id=r.id, kind="free", text_ko="예약이 확정되었습니다. 당일 여권을 지참해 주세요.",
                     text_translated="ご予約が確定しました。当日はパスポートをお持ちください。", approved_by=staff_id,
                     sent_at=c + timedelta(hours=14, minutes=5), created_at=c + timedelta(hours=14, minutes=5)))

        # 4) 방문 완료, 결제 금액 입력 전 (병원이 넣을 차례)
        p = patient(db, 4, "Emily", "en", "US", "America/Los_Angeles", kst(d(-12), 9))
        c = kst(d(-10), 9, 30)
        v = kst(d(-1), 11)
        booking(db, p, t, "US", c, v, "acne_scar", "I'd like a consultation for acne scars.",
                [("confirmed", c + timedelta(hours=3), "staff", v), ("visited", v + timedelta(hours=1, minutes=10), "staff", None)])

        # 5) 결제 확인 (카드)
        p = patient(db, 5, "Li", "zh-CN", "CN", "Asia/Shanghai", kst(d(-20), 13))
        c = kst(d(-18), 13, 20)
        v = kst(d(-9), 15)
        booking(db, p, t, "CN", c, v, "laser_toning", "想预约激光嫩肤。",
                [("proposed", c + timedelta(hours=2), "staff", v), ("confirmed", c + timedelta(hours=6), "patient", None),
                 ("visited", v + timedelta(hours=1), "staff", None), ("paid", v + timedelta(hours=1, minutes=20), "staff", None)],
                paid=(730_000, "card"))

        # 6) 결제 확인 (현금) + 사후관리 대화
        p = patient(db, 6, "Chen", "zh-TW", "TW", "Asia/Taipei", kst(d(-32), 18))
        c = kst(d(-30), 18, 30)
        v = kst(d(-21), 10, 30)
        r = booking(db, p, t, "TW", c, v, "melasma", "想治療肝斑，大概要幾次？",
                    [("confirmed", c + timedelta(hours=15), "staff", v), ("visited", v + timedelta(hours=2), "staff", None),
                     ("paid", v + timedelta(hours=2, minutes=15), "staff", None)],
                    paid=(1_860_000, "cash"))
        th = AftercareThread(request_id=r.id, tenant_id=t.id, status="in_progress", tags=["redness"],
                             created_at=kst(d(-19), 9), last_message_at=kst(d(-18), 10, 20))
        db.add(th)
        db.flush()
        for sender, text, at in [
            ("patient", "治療後臉有點紅，正常嗎？", kst(d(-19), 9)),
            ("staff", "시술 뒤 2~3일 붉은 기는 흔합니다. 진정 크림을 바르고 뜨거운 곳은 피해 주세요.", kst(d(-19), 10, 30)),
            ("patient", "好多了，謝謝！下次什麼時候可以再做？", kst(d(-18), 10, 20)),
        ]:
            db.add(AftercareMessage(thread_id=th.id, sender=sender, staff_id=staff_id if sender == "staff" else None,
                                    text_original=text, text_translated=KO.get(text) or TW.get(text), attachments=[], created_at=at))

        if args.dry_run:
            db.rollback()
        else:
            db.commit()
    print(f"가상 병원 {args.hospital}: 가상 환자 6명 (대기·시간 제안·확정·방문 완료·결제 확인 2) · 지운 것 {removed}명",
          "(dry-run, 저장 안 함)" if args.dry_run else "저장함")


if __name__ == "__main__":
    main()
