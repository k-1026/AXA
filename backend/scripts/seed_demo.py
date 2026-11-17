"""대시보드 확인용 가상 데이터 (B). **로컬 SQLite 전용** — 팀 Supabase DB에는 넣지 않음.

팀 DB에는 booking·tenant 테이블이 아직 없음 (마이그레이션은 A가 생성, 결정 13).
그 전까지는 이 스크립트로 로컬 SQLite 파일에 표를 만들고 가상 병원·요청을 넣어 대시보드를 확인한다.

    uv run --no-sync python backend/scripts/seed_demo.py            # data/dev/dashboard.db 새로 만들기
    uv run --no-sync --env-file data/dev/dashboard.env python -m uvicorn main:app --app-dir backend/src --port 8010

직원 토큰(8시간)은 data/dev/staff_token.txt에 저장 → 대시보드 주소 뒤에 `?token=...` 으로 붙여 열기.
data/dev/는 git에 올리지 않음.
실명·실제 환자 정보 없음. 환자 계정 없이 요청서만 (patient_id 비움).
"""

import random
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from sqlalchemy.orm import Session  # noqa: E402

import core.db_models  # noqa: E402,F401
from core.db import Base, make_engine  # noqa: E402
from core.security import create_access_token  # noqa: E402
from modules.aftercare.models import AftercareMessage, AftercareThread  # noqa: E402
from modules.booking.models import BookingEvent, BookingRequest, Reply  # noqa: E402
from modules.tenant.models import StaffUser, Tenant  # noqa: E402

KST = ZoneInfo("Asia/Seoul")
DB_FILE = ROOT / "data" / "dev" / "dashboard.db"
ENV_FILE = ROOT / "data" / "dev" / "dashboard.env"

LANGS = [("zh-TW", "TW"), ("zh-TW", "TW"), ("zh-TW", "TW"), ("en", "JP"), ("zh-CN", "CN"), ("en", "MN"), ("vi", "VN")]
TREATMENTS = ["laser_toning", "acne_scar", "botox", "melasma", "filler"]


def kst(d: date, h: int, m: int = 0) -> datetime:
    return datetime.combine(d, time(h, m), KST).astimezone(timezone.utc)


def add_request(db, rng, tenant, created: datetime, path: list[tuple[str, datetime]], slot: datetime | None = None):
    lang, nat = rng.choice(LANGS)
    req = BookingRequest(
        tenant_id=tenant.id,
        hospital_id=tenant.hospital_id,
        status=path[-1][0] if path else "pending",
        lang=lang,
        nationality=nat,
        contact_method="email",
        preferred_slots=[(created + timedelta(days=5)).isoformat()],
        department_code="dermatology",
        treatment=rng.choice(TREATMENTS),
        visa_needed=nat == "MN",
        message_original="(가상 문의)",
        patient_timezone="Asia/Taipei",
        confirmed_slot=slot,
        created_at=created,
        updated_at=created,
    )
    db.add(req)
    db.flush()
    db.add(BookingEvent(request_id=req.id, from_status=None, to_status="pending", actor_type="patient", created_at=created))
    prev = "pending"
    for status, when in path:
        db.add(BookingEvent(request_id=req.id, from_status=prev, to_status=status, actor_type="staff", created_at=when))
        prev = status
    return req


def seed_period(db, rng, tenant, start: date, end: date, n_req: int, n_conf: int, n_visit: int, n_cancel: int):
    days = (end - start).days + 1
    for i in range(n_req):
        d = start + timedelta(days=rng.randrange(days))
        created = kst(d, rng.randrange(9, 21))
        later = created + timedelta(hours=rng.randrange(1, 20))
        if i < n_visit:
            path = [("confirmed", later), ("visited", later + timedelta(days=2))]
        elif i < n_conf:
            path = [("confirmed", later)]
        elif i < n_conf + n_cancel:
            path = [("cancelled", later)]
        else:
            path = [("rejected", later)]
        add_request(db, rng, tenant, created, path, slot=later + timedelta(days=2))


def main() -> None:
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    if DB_FILE.exists():
        DB_FILE.unlink()
    url = "sqlite+pysqlite:///" + DB_FILE.as_posix()
    engine = make_engine(url)
    Base.metadata.create_all(engine)
    rng = random.Random(42)
    today = datetime.now(KST).date()
    month_start = today.replace(day=1)
    prev_end = month_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=(today - month_start).days)

    with Session(engine, expire_on_commit=False) as db:
        tenant = Tenant(
            hospital_id=9001,
            display_name="예시 피부과의원 (가상)",
            registration_no="DEMO-0001",
            requests_enabled=True,
            aftercare_enabled=True,
            joined_at=kst(today.replace(day=1) - timedelta(days=100), 9),
        )
        db.add(tenant)
        db.flush()
        staff = StaffUser(tenant_id=tenant.id, email="coordinator@demo.test", password_hash="(로컬 데모)", role="owner")
        db.add(staff)
        db.flush()
        # 이번 달 (요청 81 + 아래 대기 5 = 86), 지난달 같은 기간
        seed_period(db, rng, tenant, month_start, today - timedelta(days=1), 81, 29, 24, 4)
        seed_period(db, rng, tenant, prev_start, prev_end, 79, 33, 23, 3)
        # 오늘 방문 예정 2건 (확정)
        for h in (11, 15):
            add_request(db, rng, tenant, kst(today, 8), [("confirmed", kst(today, 9))], slot=kst(today, h))
        # 대기 5건 (1건은 답장 보냄) — 대시보드 상담 채팅에 보일 가상 문의
        pending = [
            ("zh-TW", "TW", "laser_toning", False, "你好，我11月20日到24日在大邱，想做雷射淨膚，請問需要幾次？",
             "안녕하세요, 11월 20~24일 대구에 있어요. 레이저 토닝을 받고 싶은데 몇 회가 필요한가요?"),
            ("en", "MN", "acne_scar", True, "Hello, I need a reservation confirmation letter for my medical visa. Is 21 Nov possible?",
             "의료 비자용 예약확인서가 필요해요. 11월 21일 가능한가요?"),
            ("zh-CN", "CN", "botox", False, "想预约肉毒素，周六可以吗？", "보톡스 예약하고 싶어요. 토요일 가능한가요?"),
            ("vi", "VN", "melasma", False, "Tôi muốn điều trị nám, cuối tuần có lịch không?", "기미 치료를 받고 싶어요. 주말에 예약 가능한가요?"),
            ("zh-TW", "TW", "filler", False, "請問玻尿酸的價格範圍？", "필러 가격 범위가 궁금해요."),
        ]
        for i, (lang, nat, trt, visa, orig, ko) in enumerate(pending):
            req = add_request(db, rng, tenant, kst(today, 9 + i), [])
            req.lang, req.nationality, req.treatment, req.visa_needed = lang, nat, trt, visa
            req.message_original, req.message_translated = orig, ko
            req.preferred_slots = [kst(today + timedelta(days=4 + i), 10).isoformat(), kst(today + timedelta(days=5 + i), 14).isoformat()]
            if i == 4:
                db.add(Reply(request_id=req.id, text_ko="(가상 답장)", sent_at=kst(today, 10), approved_by=staff.id))
        # 사후관리 대화 3개 (방문 완료 요청에 연결)
        visited = [r for r in db.query(BookingRequest).filter_by(tenant_id=tenant.id, status="visited").order_by(BookingRequest.created_at.desc()).limit(3)]
        threads = [
            ("new", ["붉은기"], [("patient", "做完第三天了，臉還是有點紅，這樣正常嗎？", "시술 3일째인데 얼굴이 아직 조금 빨개요. 정상인가요?", True)]),
            ("in_progress", ["영수증 재발급"], [
                ("patient", "保険の申請のため、英語の領収書をもう一度いただけますか？", "보험 청구 때문에 영문 영수증을 다시 받을 수 있을까요?", False),
                ("staff", "네, 내일 오전까지 메일로 보내드릴게요.", "はい、明日の午前中までにメールでお送りします。", False)]),
            ("resolved", ["재방문 일정"], [
                ("patient", "下一次療程什麼時候可以做？", "다음 시술은 언제 받을 수 있나요?", False),
                ("staff", "4주 뒤부터 가능해요. 12월 6일(토) 11시로 예약해 드릴까요?", "4週後から可能です。", False),
                ("patient", "好的，謝謝！", "네, 감사합니다!", False)]),
        ]
        for req, (status, tags, msgs) in zip(visited, threads):
            th = AftercareThread(request_id=req.id, tenant_id=tenant.id, status=status, tags=tags)
            db.add(th)
            db.flush()
            for j, (sender, orig, tr, photo) in enumerate(msgs):
                db.add(AftercareMessage(thread_id=th.id, sender=sender, staff_id=staff.id if sender == "staff" else None,
                                        text_original=orig, text_translated=tr, has_photo=photo,
                                        created_at=kst(today, 8) - timedelta(days=len(msgs) - j)))
        db.commit()
        token = create_access_token(str(staff.id), "staff", tenant_id=str(tenant.id))

    ENV_FILE.write_text(
        f"DATABASE_URL={url}\nCORS_ORIGINS='[\"http://localhost:5176\",\"http://localhost:5175\"]'\nDISABLE_SQLALCHEMY_CEXT=1\n",
        encoding="utf-8",
    )
    print(f"로컬 DB: {DB_FILE}")
    print(f"서버 환경 파일: {ENV_FILE}")
    (ENV_FILE.parent / "staff_token.txt").write_text(token, encoding="utf-8")
    print(f"직원 토큰(8시간): {ENV_FILE.parent / 'staff_token.txt'} → 대시보드 주소 뒤에 ?token=<값>")


if __name__ == "__main__":
    main()
