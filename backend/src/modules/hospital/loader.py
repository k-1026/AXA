"""공공데이터 CSV → hospitals·hospital_hours·hospital_departments (ykiho로 upsert).

파일은 경로로 받는다 (데이터 파일을 백엔드에 복사하지 않음). 없는 파일은 건너뜀.
- hospitals_csv: data/interim/영업정보/daegu_hospitals.csv (심평원 병원정보, 필수)
- hours_csv: data/interim/영업정보/daegu_hospital_hours.csv (진료시간·피부과·성형외과 여부)
- status_csv: data/processed/daegu_hospital_status.csv (영업 판정 verdict)
- registered_csv: data/processed/daegu_registered_institutions.csv (유치의료기관 등록, research-data 브랜치)
- dgsbjt_json: data/raw/영업정보/daegu_dgsbjt_hospitals.json (내과 01·안과 12, research-data 브랜치)
"""

import csv
import json
import re
from datetime import datetime, time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.db import utcnow
from modules.hospital.models import Department, Hospital, HospitalDepartment, HospitalHours

SOURCE = "건강보험심사평가원 병원정보서비스"
DEPARTMENTS = {"dermatology": "14", "plastic": "08", "internal": "01", "ophthalmology": "12"}
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
VERDICT = {"정상": "normal", "폐업": "closed"}  # 그 밖(미확인 등)은 unknown


def _rows(path: Path | str | None) -> list[dict[str, str]]:
    if path is None or not Path(path).exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]


def _float(v: str) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _hhmm(v: str) -> time | None:
    if not re.fullmatch(r"\d{4}", v or ""):
        return None
    h, m = int(v[:2]), int(v[2:])
    if h == 24 and m == 0:
        return time(23, 59)
    return time(h, m) if h < 24 and m < 60 else None


_LUNCH = re.compile(r"(\d{1,2})\s*시\s*(\d{1,2})?\s*분?\s*[~\-]\s*(\d{1,2})\s*시\s*(\d{1,2})?")


def _lunch(text: str) -> tuple[time | None, time | None]:
    m = _LUNCH.search(text or "")
    if not m:
        return None, None
    try:
        return time(int(m[1]), int(m[2] or 0)), time(int(m[3]), int(m[4] or 0))
    except ValueError:
        return None, None


def _dgsbjt(path: Path | str | None) -> dict[str, set[str]]:
    """내과·안과 ykiho 목록."""
    if path is None or not Path(path).exists():
        return {}
    items = json.loads(Path(path).read_text(encoding="utf-8")).get("items", {})
    code_to_dept = {v: k for k, v in DEPARTMENTS.items()}
    return {
        code_to_dept[code]: {i["ykiho"] for i in rows}
        for code, rows in items.items()
        if code in code_to_dept
    }


def _hours(row: dict[str, str], now: datetime) -> list[HospitalHours]:
    lunch_week = _lunch(row.get("lunchWeek", ""))
    lunch_sat = _lunch(row.get("lunchSat", ""))
    out = []
    for i, day in enumerate(DAYS):
        cap = day.capitalize()
        open_t, close_t = _hhmm(row.get(f"trmt{cap}Start", "")), _hhmm(row.get(f"trmt{cap}End", ""))
        memo = row.get("noTrmtSun") if day == "sun" else None
        if open_t and close_t and open_t != close_t:  # 원본 "0000~0000"(시작=끝)은 진료로 보지 않음
            state = "open"
        elif day == "sun" and "휴" in (memo or ""):
            state = "closed"
        else:
            state = "unknown"  # 값이 없다고 휴진으로 단정하지 않음
        lunch = lunch_sat if day == "sat" else (lunch_week if day != "sun" else (None, None))
        out.append(
            HospitalHours(
                day=day,
                day_order=i,
                open_time=open_t if state == "open" else None,
                close_time=close_t if state == "open" else None,
                lunch_start=lunch[0] if state == "open" else None,
                lunch_end=lunch[1] if state == "open" else None,
                memo_ko=memo or None,
                state=state,
                source=SOURCE,
                checked_at=now,
            )
        )
    return out


def load_hospitals(
    db: Session,
    hospitals_csv: Path | str,
    *,
    hours_csv: Path | str | None = None,
    status_csv: Path | str | None = None,
    registered_csv: Path | str | None = None,
    dgsbjt_json: Path | str | None = None,
    fetched_at: datetime | None = None,
) -> dict[str, int]:
    """적재 후 커밋은 호출하는 쪽에서. 반환: 건수 요약."""
    now = fetched_at or utcnow()
    for code, hira in DEPARTMENTS.items():
        db.merge(Department(code=code, hira_code=hira))

    hours = {r["ykiho"]: r for r in _rows(hours_csv)}
    verdict = {r["ykiho"]: VERDICT.get(r.get("verdict", ""), "unknown") for r in _rows(status_csv)}
    registered = {r["ykiho"]: r for r in _rows(registered_csv) if r.get("ykiho")}
    dept_sets = _dgsbjt(dgsbjt_json)

    existing = {h.ykiho: h for h in db.scalars(select(Hospital).where(Hospital.is_demo.is_(False)))}
    seen: set[str] = set()
    counts = {"loaded": 0, "registered": 0, "closed": 0}

    for r in _rows(hospitals_csv):
        yk = r.get("ykiho")
        if not yk or yk in seen:
            continue
        seen.add(yk)
        h = existing.get(yk) or Hospital(ykiho=yk)
        if h.id is None:
            db.add(h)
        reg = registered.get(yk)
        h.name_ko = r.get("yadmNm", "")
        h.name_en = (reg or {}).get("name_en") or None
        h.addr_en = (reg or {}).get("address_en") or None
        h.type_code = r.get("clCd") or None
        h.type_name_ko = r.get("clCdNm") or None
        h.sggu = r.get("sgguCdNm") or None
        h.addr_ko = r.get("addr") or None
        h.tel = r.get("telno") or None
        h.lng, h.lat = _float(r.get("XPos", "")), _float(r.get("YPos", ""))
        h.homepage = r.get("hospUrl") or None
        h.is_registered_facility = reg is not None
        h.status_verdict = verdict.get(yk, "normal" if not status_csv else "unknown")
        h.is_demo = False
        h.source = SOURCE
        h.fetched_at = now

        hr = hours.get(yk)
        depts = {d for d, ids in dept_sets.items() if yk in ids}
        if hr:
            # 피부과·성형외과 = 진료과목에 있고 **이름에도 과 이름이 있는 전문 병원**만 (2026-11-17 결정).
            # 진료과목만 보면 대학병원·한방병원·다른 과 의원까지 섞임 → 피부과 818 → 80곳, 성형외과 256 → 70곳
            name = r.get("yadmNm", "")
            if hr.get("has_dermatology") == "Y" and "피부과" in name:
                depts.add("dermatology")
            if hr.get("has_plastic_surgery") == "Y" and "성형외과" in name:
                depts.add("plastic")
            h.hours = _hours(hr, now)
        h.departments = [HospitalDepartment(dept_code=d) for d in sorted(depts)]

        counts["loaded"] += 1
        counts["registered"] += reg is not None

    # 새 파일에 없는 병원 = 폐업 처리 (행은 남김 → id 유지)
    for yk, h in existing.items():
        if yk not in seen and h.status_verdict != "closed":
            h.status_verdict = "closed"
            counts["closed"] += 1
    db.flush()
    return counts
