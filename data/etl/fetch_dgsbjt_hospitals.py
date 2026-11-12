"""심평원 병원정보서비스에서 대구 진료과목별 병원 목록을 받는다.

용도: 내과(01)·안과(12) 판정을 '병원 이름' 대신 진료과목 코드로 바꾸기 위함
(apps/web-platform/scripts/build-hospitals.mjs 의 임시 기준 교체)

실행: python3 data/etl/fetch_dgsbjt_hospitals.py   (.env 의 DATA_GO_KR_SERVICE_KEY 사용)
결과: data/raw/영업정보/daegu_dgsbjt_hospitals.json
"""
import json
import os
import pathlib
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "data/raw/영업정보/daegu_dgsbjt_hospitals.json"
URL = "https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList"
CODES = {"01": "내과", "12": "안과"}
SIDO_DAEGU = "230000"


def load_key():
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("DATA_GO_KR_SERVICE_KEY="):
            return line.split("=", 1)[1].strip()
    return os.environ["DATA_GO_KR_SERVICE_KEY"]


def fetch(key, code):
    items, page = [], 1
    while True:
        q = urllib.parse.urlencode({"pageNo": page, "numOfRows": 500, "sidoCd": SIDO_DAEGU, "dgsbjtCd": code, "_type": "json"})
        with urllib.request.urlopen(f"{URL}?serviceKey={key}&{q}", timeout=60) as r:
            body = json.load(r)["response"]["body"]
        got = body["items"]["item"] if body.get("items") else []
        got = [got] if isinstance(got, dict) else got
        items += got
        if len(items) >= body["totalCount"] or not got:
            return items, body["totalCount"]
        page += 1
        time.sleep(0.3)


def main():
    key = load_key()
    result = {}
    for code, name in CODES.items():
        items, total = fetch(key, code)
        result[code] = [{"ykiho": i["ykiho"], "yadmNm": i["yadmNm"], "clCdNm": i["clCdNm"], "sgguCdNm": i.get("sgguCdNm")} for i in items]
        print(f"{code} {name}: {len(items)} / {total}")
    OUT.write_text(json.dumps({
        "meta": {
            "source": "건강보험심사평가원_병원정보서비스 getHospBasisList (sidoCd 230000, dgsbjtCd 01 내과·12 안과)",
            "url": "https://www.data.go.kr/data/15001698/openapi.do",
            "license": "공공누리 제1유형(출처표시)",
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
            "counts": {c: len(v) for c, v in result.items()},
        },
        "items": result,
    }, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
