"""병원 공공정보 적재. 실행 (저장소 맨 위에서):

    uv run python backend/scripts/load_hospitals.py            # .env의 DATABASE_URL로
    uv run python backend/scripts/load_hospitals.py --dry-run  # 건수만 보고 저장 안 함

등록 유치의료기관·내과/안과·진료시간 직접 채움 파일은 research-data 브랜치에 있음. 없으면 건너뛰고 경고만
(그러면 모든 병원이 미등록 → 요청 가능한 병원 0곳).
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend/src"))

from sqlalchemy.orm import Session  # noqa: E402

from core.db import get_engine  # noqa: E402
from modules.hospital.loader import load_hospitals  # noqa: E402

DEFAULTS = {
    "hospitals_csv": "data/interim/영업정보/daegu_hospitals.csv",
    "hours_csv": "data/interim/영업정보/daegu_hospital_hours.csv",
    "status_csv": "data/processed/daegu_hospital_status.csv",
    "registered_csv": "data/processed/daegu_registered_institutions.csv",
    "dgsbjt_json": "data/raw/영업정보/daegu_dgsbjt_hospitals.json",
    # 등록 유치기관 진료시간 직접 채움 (research-data 브랜치). API 빈 요일만 채움
    "manual_hours_csv": "data/processed/daegu_hours_manual.csv",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_', '-')}", default=str(ROOT / v))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    paths = {k: Path(getattr(args, k)) for k in DEFAULTS}
    for k, p in paths.items():
        if not p.exists():
            print(f"경고: {k} 없음 → 건너뜀 ({p})", file=sys.stderr)
    with Session(get_engine()) as db:
        counts = load_hospitals(db, **paths)
        if args.dry_run:
            db.rollback()
        else:
            db.commit()
    print(counts, "(dry-run, 저장 안 함)" if args.dry_run else "저장함")


if __name__ == "__main__":
    main()
