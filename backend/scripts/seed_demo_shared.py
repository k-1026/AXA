"""시연용 가상 병원 9001을 공용 DB(Supabase)에서 쓸 수 있게 채운다 (A). 여러 번 돌려도 같은 결과.

    uv run --no-sync python backend/scripts/seed_demo_shared.py             # .env의 DATABASE_URL로
    uv run --no-sync python backend/scripts/seed_demo_shared.py --dry-run   # 바뀔 내용만 보고 저장 안 함

하는 일 (실제 병원은 건드리지 않음 — compliance 2-6: 예시 일정·예약은 가상 병원에만)
1. 가상 병원 9001 (`is_demo`): 이름·가상 주소·좌표·진료시간·진료과를 `data/processed/demo/demo_hospital.json` 값으로
   (없으면 새로 만듦, 환자 웹 목록도 같은 파일을 읽음)
2. 입점 계정(tenant): 9001에 없으면 만들고, 요청·사후관리 받기 켬
3. 시연 직원 계정 `demo-staff@example.com` — 대시보드 로그인용 (`POST /auth/staff/login`)
4. 시연 환자 계정 `demo-patient@example.com` + 그 환자의 예약 2건 (방문 완료·확정). 다시 돌리면 이 환자 예약만 새로 만듦
   B가 넣은 9001 대시보드 데이터(환자 없는 요청)는 그대로 둠

비밀번호: 계정을 처음 만들 때만 새로 만들어 `data/dev/demo_accounts.txt`(git 제외)에 저장.
이미 있으면 바꾸지 않음 (`--reset-passwords`로 새로 만들 수 있음). 실명·실제 환자 정보 없음.
"""

import argparse
import json
import secrets
import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import core.db_models  # noqa: E402,F401
from core.db import get_engine  # noqa: E402
from modules.auth.service import password_hash  # noqa: E402
from modules.booking.models import BookingEvent, BookingRequest  # noqa: E402
from modules.consent.models import Consent  # noqa: E402
from modules.consent.service import CURRENT_VERSIONS  # noqa: E402

OVERSEAS_VERSION = "2026-11-18"  # 번역 안내 문구 날짜 (환자 웹 bookingApi.ts OVERSEAS_VERSION과 같게)
from modules.hospital.models import Hospital, HospitalDepartment, HospitalHours  # noqa: E402
from modules.patient.models import Patient  # noqa: E402
from modules.tenant.models import StaffUser, Tenant  # noqa: E402

KST = ZoneInfo("Asia/Seoul")
DEMO_FILE = ROOT / "data" / "processed" / "demo" / "demo_hospital.json"
ACCOUNTS_FILE = ROOT / "data" / "dev" / "demo_accounts.txt"
STAFF_EMAIL = "demo-staff@example.com"
PATIENT_EMAIL = "demo-patient@example.com"
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _t(v: str) -> time:
    h, m = v.split(":")
    return time(int(h), int(m))


def kst(d, h: int, m: int = 0) -> datetime:
    return datetime.combine(d, time(h, m), KST).astimezone(timezone.utc)


def seed_hospital(db: Session, demo: dict, now: datetime) -> Hospital:
    h = db.get(Hospital, demo["id"])
    if h is None:
        h = Hospital(id=demo["id"], ykiho=demo["ykiho"], fetched_at=now)
        db.add(h)
    for k in ("ykiho", "name_ko", "name_en", "type_code", "type_name_ko", "sggu", "addr_ko", "addr_en", "lat", "lng", "source"):
        setattr(h, k, demo[k])
    h.tel = None
    h.homepage = None
    h.is_demo = True
    h.is_registered_facility = True  # 가상 병원도 요청 흐름을 보여 주려면 "등록"으로 둠 (is_demo로 구분)
    h.status_verdict = "normal"
    h.fetched_at = now
    db.flush()
    # 요일·진료과는 그 자리에서 고침 (지우고 같은 키로 다시 넣으면 INSERT가 먼저 나가 키 충돌)
    lunch = demo.get("lunch") or [None, None]
    by_day = {x.day: x for x in h.hours}
    for i, day in enumerate(DAYS):
        v = demo["hours"].get(day)
        row = by_day.get(day)
        if row is None:
            row = HospitalHours(day=day)
            h.hours.append(row)
        row.day_order = i
        row.open_time = _t(v[0]) if v else None
        row.close_time = _t(v[1]) if v else None
        weekday_lunch = bool(v and lunch[0] and day != "sat")
        row.lunch_start = _t(lunch[0]) if weekday_lunch else None
        row.lunch_end = _t(lunch[1]) if weekday_lunch else None
        row.memo_ko = None if v else "휴진 (가상)"
        row.state = "open" if v else "closed"
        row.source = demo["source"]
        row.checked_at = now
    have = {d.dept_code for d in h.departments}
    for d in list(h.departments):
        if d.dept_code not in demo["depts"]:
            h.departments.remove(d)
    for c in demo["depts"]:
        if c not in have:
            h.departments.append(HospitalDepartment(dept_code=c))
    db.flush()
    return h


def seed_tenant(db: Session, h: Hospital, now: datetime) -> Tenant:
    t = db.scalar(select(Tenant).where(Tenant.hospital_id == h.id))
    if t is None:
        t = Tenant(hospital_id=h.id, display_name=h.name_ko, registration_no="DEMO-0001", joined_at=now - timedelta(days=100))
        db.add(t)
    t.requests_enabled = True
    t.aftercare_enabled = True
    db.flush()
    return t


def _password(existing: str | None, reset: bool) -> tuple[str | None, str | None]:
    """(새 비밀번호, 해시). 기존 계정이고 reset이 아니면 (None, None) → 바꾸지 않음."""
    if existing is not None and not reset:
        return None, None
    pw = "Demo-" + secrets.token_urlsafe(9)
    return pw, password_hash.hash(pw)


def seed_staff(db: Session, t: Tenant, reset: bool) -> str | None:
    s = db.scalar(select(StaffUser).where(StaffUser.email == STAFF_EMAIL))
    pw, hashed = _password(s and s.password_hash, reset)
    if s is None:
        s = StaffUser(tenant_id=t.id, email=STAFF_EMAIL, password_hash=hashed, role="owner")
        db.add(s)
    elif hashed:
        s.password_hash = hashed
    s.tenant_id = t.id
    s.disabled_at = None
    db.flush()
    return pw


def seed_patient(db: Session, reset: bool, now: datetime) -> tuple[Patient, str | None]:
    p = db.scalar(select(Patient).where(Patient.email == PATIENT_EMAIL))
    pw, hashed = _password(p and p.password_hash, reset)
    if p is None:
        p = Patient(email=PATIENT_EMAIL, password_hash=hashed, display_name="Demo Patient", preferred_lang="zh-TW",
                    timezone="Asia/Taipei", age14_confirmed_at=now)
        db.add(p)
        db.flush()
        for kind, version in CURRENT_VERSIONS.items():
            db.add(Consent(patient_id=p.id, kind=kind, version=version, lang="zh-TW", agreed_at=now))
    elif hashed:
        p.password_hash = hashed
    db.flush()
    return p, pw


def seed_patient_bookings(db: Session, p: Patient, t: Tenant, now: datetime) -> int:
    """시연 환자 예약 2건(방문 완료·확정)을 새로 만든다 (이 환자의 기존 예약은 지움).
    대기(pending) 예약은 넣지 않음 — 같은 병원에 대기·제안 요청이 있으면 새 요청이 409 booking.duplicate라
    시연 때 환자가 직접 요청하는 장면을 못 보여 줌. 시연 중에 만든 요청도 다시 돌리면 지워짐 (리허설 초기화)"""
    old_ids = list(db.scalars(select(BookingRequest.id).where(BookingRequest.patient_id == p.id)))
    if old_ids:  # DB의 ON DELETE에 기대지 않고 직접 지움 (SQLite 로컬 확인에서도 같은 결과)
        db.execute(delete(BookingEvent).where(BookingEvent.request_id.in_(old_ids)))
        db.execute(delete(Consent).where(Consent.booking_request_id.in_(old_ids)))
        db.execute(delete(BookingRequest).where(BookingRequest.id.in_(old_ids)))
    db.flush()
    today = now.astimezone(KST).date()
    plans = [
        # (상태, 만든 날, 확정 시간, 진료항목, 문의, 문의 한국어 — 시드는 LLM을 부르지 않고 미리 쓴 번역)
        ("visited", today - timedelta(days=12), kst(today - timedelta(days=7), 11), "laser_toning", "想做雷射淨膚，大概需要幾次？",
         "레이저 토닝을 하고 싶은데, 대략 몇 번 받아야 하나요?"),
        ("confirmed", today - timedelta(days=3), kst(today + timedelta(days=4), 14), "acne_scar", "痘疤治療可以預約嗎？",
         "여드름 흉터 치료 예약할 수 있나요?"),
    ]
    for status, created_day, slot, treatment, msg, msg_ko in plans:
        created = kst(created_day, 10)
        req = BookingRequest(
            patient_id=p.id, tenant_id=t.id, hospital_id=t.hospital_id, status=status, lang="zh-TW", nationality="TW",
            contact_method="email", department_code="dermatology", treatment=treatment, visa_needed=False,
            preferred_slots=[(slot or kst(today + timedelta(days=6), 11)).isoformat()],
            message_original=msg, message_translated=msg_ko, patient_timezone="Asia/Taipei", confirmed_slot=slot, created_at=created, updated_at=created,
        )
        db.add(req)
        db.flush()
        db.add(Consent(patient_id=p.id, booking_request_id=req.id, kind="privacy", version=CURRENT_VERSIONS["privacy"],
                       lang="zh-TW", agreed_at=created))
        # 문의 글이 있으면 실제 요청서처럼 번역(해외 LLM) 동의도 → 시연에서 사후관리·답장 번역이 보임 (결정 25)
        db.add(Consent(patient_id=p.id, booking_request_id=req.id, kind="overseas_transfer", version=OVERSEAS_VERSION,
                       lang="zh-TW", agreed_at=created))
        db.add(BookingEvent(request_id=req.id, from_status=None, to_status="pending", actor_type="patient", created_at=created))
        prev = "pending"
        for nxt, at in {"confirmed": [("confirmed", created + timedelta(hours=3))],
                        "visited": [("confirmed", created + timedelta(hours=3)), ("visited", slot + timedelta(hours=1) if slot else created)],
                        }.get(status, []):
            db.add(BookingEvent(request_id=req.id, from_status=prev, to_status=nxt, actor_type="staff", created_at=at))
            prev = nxt
    db.flush()
    return len(plans)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reset-passwords", action="store_true")
    args = ap.parse_args()
    demo = json.loads(DEMO_FILE.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    with Session(get_engine()) as db:
        h = seed_hospital(db, demo, now)
        t = seed_tenant(db, h, now)
        staff_pw = seed_staff(db, t, args.reset_passwords)
        p, patient_pw = seed_patient(db, args.reset_passwords, now)
        n = seed_patient_bookings(db, p, t, now)
        if args.dry_run:
            db.rollback()
        else:
            db.commit()
    print(f"가상 병원 {demo['id']} · tenant · 직원 · 환자 · 환자 예약 {n}건", "(dry-run, 저장 안 함)" if args.dry_run else "저장함")
    if args.dry_run:
        return
    if staff_pw or patient_pw:
        ACCOUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        lines = ACCOUNTS_FILE.read_text(encoding="utf-8").splitlines() if ACCOUNTS_FILE.exists() else []
        keep = [x for x in lines if not ((staff_pw and x.startswith(STAFF_EMAIL)) or (patient_pw and x.startswith(PATIENT_EMAIL)))]
        if staff_pw:
            keep.append(f"{STAFF_EMAIL} {staff_pw}  (병원 직원 · 대시보드)")
        if patient_pw:
            keep.append(f"{PATIENT_EMAIL} {patient_pw}  (환자 · 환자 웹)")
        ACCOUNTS_FILE.write_text("\n".join(keep) + "\n", encoding="utf-8")
        print(f"새 비밀번호 → {ACCOUNTS_FILE} (git 제외)")
    else:
        print(f"비밀번호는 그대로 ({ACCOUNTS_FILE})")


if __name__ == "__main__":
    main()
