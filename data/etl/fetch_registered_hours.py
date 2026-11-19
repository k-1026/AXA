"""등록 유치기관 진료시간 빈칸 채우기용 공공 API 수집 (2026-11-18).

1) 국립중앙의료원 전국 병·의원 찾기 서비스 (getHsptlMdcncListInfoInqire, Q0=대구광역시) 전체
   → data/raw/영업정보/daegu_nmc_hospitals.json
2) 심평원 의료기관별상세정보서비스 getDtlInfo2.8 다시 받기 (작업표의 ykiho·후보 ykiho만)
   → data/raw/영업정보/registered_hira_detail_2026-11-18.json

인증키는 .env의 DATA_GO_KR_SERVICE_KEY (출력하지 않음). 실행: python data/etl/fetch_registered_hours.py
"""
import csv, json, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KEY = next(l.split("=", 1)[1].strip().strip('"') for l in open(ROOT / ".env", encoding="utf-8") if l.startswith("DATA_GO_KR_SERVICE_KEY="))
TODAY = date.today().isoformat()


def call(url, params):
    k = KEY if "%" in KEY else urllib.parse.quote(KEY, safe="")
    u = f"{url}?serviceKey={k}&{urllib.parse.urlencode(params)}"
    for i in range(3):
        try:
            with urllib.request.urlopen(u, timeout=30) as r:
                return r.read().decode("utf-8")
        except Exception:
            time.sleep(2 * (i + 1))
    raise RuntimeError("API 호출 실패: " + url)


def nmc_all():
    url = "https://apis.data.go.kr/B552657/HsptlAsembySearchService/getHsptlMdcncListInfoInqire"
    items, page = [], 1
    while True:
        root = ET.fromstring(call(url, {"Q0": "대구광역시", "pageNo": page, "numOfRows": 1000}))
        assert root.findtext("header/resultCode") == "00", root.findtext("header/resultMsg")
        got = [{c.tag: (c.text or "") for c in it} for it in root.iter("item")]
        items += got
        total = int(root.findtext("body/totalCount") or 0)
        if not got or len(items) >= total:
            return items, total
        page += 1


def hira_detail(ykihos):
    url = "https://apis.data.go.kr/B551182/MadmDtlInfoService2.8/getDtlInfo2.8"
    out = {}
    for y in ykihos:
        d = json.loads(call(url, {"ykiho": y, "_type": "json"}))
        item = (d["response"]["body"].get("items") or {})
        item = item.get("item") if isinstance(item, dict) else None
        out[y] = item or {}
        time.sleep(0.1)
    return out


if __name__ == "__main__":
    raw = ROOT / "data/raw/영업정보"
    items, total = nmc_all()
    (raw / "daegu_nmc_hospitals.json").write_text(json.dumps(
        {"source": "국립중앙의료원_전국 병·의원 찾기 서비스 getHsptlMdcncListInfoInqire (Q0=대구광역시)",
         "fetchedAt": TODAY, "totalCount": total, "items": items}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("NMC", len(items), "/", total)

    rows = list(csv.DictReader(open(ROOT / "data/interim/영업정보/registered_hours_fill.csv", encoding="utf-8-sig")))
    ys = sorted({r["ykiho"] for r in rows if r["ykiho"] and r["status"] != "filled"} | {r["candidate_ykiho"] for r in rows if r["candidate_ykiho"]})
    det = hira_detail(ys)
    (raw / "registered_hira_detail_2026-11-18.json").write_text(json.dumps(
        {"source": "건강보험심사평가원_의료기관별상세정보서비스 getDtlInfo2.8", "fetchedAt": TODAY, "items": det},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("HIRA", len(det), "건, 진료시간 있는 곳", sum(1 for v in det.values() if any(v.get(f"trmt{d}Start") for d in ["Mon","Tue","Wed","Thu","Fri"])))
