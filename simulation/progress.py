"""진행 상황 기록 — 대시보드(dashboard/index.html)가 output/progress.json을 읽어 보여 준다.

사용: python3 simulation/progress.py <단계번호> <pending|doing|done> "메모"
"""
import json
import sys
from datetime import datetime
from pathlib import Path

PATH = Path(__file__).parent / "output" / "progress.json"

STEPS = [
    "폴더·원본 보관·대시보드",
    "실습양식 엑셀 구조·수식 파악",
    "엑셀 생성 스크립트 (비용·전환·현금흐름)",
    "결과 계산·수식 검증",
    "verify.md 숫자 검증",
    "pnl_sim.md 요약",
    "대시보드 결과 반영·최종 확인",
]


def load():
    if PATH.exists():
        return json.loads(PATH.read_text(encoding="utf-8"))
    return {"steps": [{"name": n, "status": "pending", "note": ""} for n in STEPS], "log": []}


def main():
    data = load()
    if sys.argv[1] == "add":  # python3 progress.py add "단계 이름"
        data["steps"].append({"name": sys.argv[2], "status": "pending", "note": ""})
        PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    i, status = int(sys.argv[1]) - 1, sys.argv[2]
    note = sys.argv[3] if len(sys.argv) > 3 else ""
    data["steps"][i]["status"] = status
    if note:
        data["steps"][i]["note"] = note
    now = datetime.now().strftime("%m-%d %H:%M")
    data["log"].insert(0, {"time": now, "step": i + 1, "status": status, "note": note})
    data["updated"] = now
    PATH.parent.mkdir(exist_ok=True)
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
