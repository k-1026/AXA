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
        # 대기 5건 (1건은 답장 보냄)
        for i in range(5):
            req = add_request(db, rng, tenant, kst(today, 9 + i), [])
            if i == 0:
                db.add(Reply(request_id=req.id, text_ko="(가상 답장)", sent_at=kst(today, 10), approved_by=staff.id))
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
