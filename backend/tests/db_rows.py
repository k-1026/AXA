"""테스트용 가상 행. conftest가 SQLite FK 검사를 켜므로 FK가 가리키는 행을 먼저 만든다 (Postgres와 같은 동작)."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from modules.hospital.models import Hospital


def demo_hospital(db: Session, hospital_id: int = 9001) -> Hospital:
    """가상 병원(`is_demo`) 행. 이미 있으면 그대로 돌려줌. 실제 병원 이름·ykiho 사용 X."""
    h = db.get(Hospital, hospital_id)
    if h is None:
        h = Hospital(
            id=hospital_id,
            ykiho=f"DEMO-{hospital_id}",
            name_ko=f"가상 병원 {hospital_id}",
            is_registered_facility=True,
            is_demo=True,
            source="test",
            fetched_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        )
        db.add(h)
        db.flush()
    return h


def demo_staff(db: Session, tenant_id, email: str | None = None):
    """가상 직원 행. 답장·사후관리 메시지의 staff_id FK(→ staff_users)가 가리킬 대상."""
    import uuid

    from modules.tenant.models import StaffUser

    s = StaffUser(tenant_id=tenant_id, email=email or f"staff-{uuid.uuid4().hex[:8]}@demo.test",
                  password_hash="(test)", role="staff")
    db.add(s)
    db.commit()
    return s


def demo_partner(db: Session, hospital_id: int = 9002, depts: tuple[str, ...] = ("dermatology",)) -> Hospital:
    """메디대구 입점 가상 병원 (진료과 + 요청 받는 tenant). 챗봇 조건 맞춤 제안·예약 대상 (결정 31)."""
    from datetime import time

    from modules.hospital.models import Department, HospitalDepartment, HospitalHours
    from modules.tenant.models import Tenant

    for c in depts:  # 진료과 코드 표 (적재 스크립트가 넣는 값)
        if db.get(Department, c) is None:
            db.add(Department(code=c))
    db.flush()
    h = demo_hospital(db, hospital_id)
    h.name_en = f"Demo Clinic {hospital_id}"
    h.sggu = "대구수성구"
    h.status_verdict = "normal"
    for c in depts:
        h.departments.append(HospitalDepartment(dept_code=c))
    for i, day in enumerate(("mon", "tue", "wed", "thu", "fri", "sat", "sun")):
        open_ = day != "sun"
        h.hours.append(HospitalHours(day=day, day_order=i, state="open" if open_ else "closed",
                                     open_time=time(10) if open_ else None, close_time=time(18) if open_ else None,
                                     source="test", checked_at=datetime(2026, 11, 1, tzinfo=timezone.utc)))
    db.add(Tenant(hospital_id=h.id, display_name=h.name_ko, requests_enabled=True, registration_no=f"DEMO-{hospital_id}"))
    db.commit()
    return h
