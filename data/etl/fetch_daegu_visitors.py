"""한국관광공사 빅데이터 지역별 방문자수 API에서 대구 방문자(현지인·외지인·외국인)를 일자별로 받는다.

- 광역: 대구광역시 (areaCode 27)
- 기초: 대구 구·군 (signguCode 27로 시작)
- 외국인 = SK텔레콤 이동통신 기반 추정, 기초·광역 집계 기준이 달라 합산하지 말 것 (API 안내)

실행: python3 data/etl/fetch_daegu_visitors.py [시작YYYYMMDD] [끝YYYYMMDD]   (.env 의 DATA_GO_KR_SERVICE_KEY)
결과: data/raw/유입/daegu_visitors_daily.json
"""
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "data/raw/유입/daegu_visitors_daily.json"
BASE = "https://apis.data.go.kr/B551011/DataLabService/"


def load_key():
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("DATA_GO_KR_SERVICE_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("DATA_GO_KR_SERVICE_KEY 없음")


def call(key, op, start, end, page):
    q = urllib.parse.urlencode({"MobileOS": "ETC", "MobileApp": "AXA", "startYmd": start, "endYmd": end,
                                "numOfRows": 10000, "pageNo": page, "_type": "json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(f"{BASE}{op}?serviceKey={key}&{q}", timeout=120) as r:
                body = json.load(r)["response"]["body"]
            items = body["items"]["item"] if body.get("items") else []
            return ([items] if isinstance(items, dict) else items), int(body.get("totalCount", 0))
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)


def fetch(key, op, start, end, keep):
    out = []
    d = datetime.strptime(start, "%Y%m%d").date()
    last = datetime.strptime(end, "%Y%m%d").date()
    while d <= last:
        e = min(d + timedelta(days=29), last)
        page = 1
        while True:
            items, total = call(key, op, d.strftime("%Y%m%d"), e.strftime("%Y%m%d"), page)
            out += [i for i in items if keep(i)]
            if page * 10000 >= total or not items:
                break
            page += 1
        d = e + timedelta(days=1)
        time.sleep(0.2)
    return out


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else "20240101"
    end = sys.argv[2] if len(sys.argv) > 2 else (date.today() - timedelta(days=1)).strftime("%Y%m%d")
    key = load_key()
    metro = fetch(key, "metcoRegnVisitrDDList", start, end, lambda i: i.get("areaCode") == "27")
    local = fetch(key, "locgoRegnVisitrDDList", start, end, lambda i: str(i.get("signguCode", "")).startswith("27"))
    slim = lambda i, k: {"date": i["baseYmd"], "area": i.get(k), "type": i["touDivNm"], "n": round(float(i["touNum"]), 1)}
    OUT.write_text(json.dumps({
        "meta": {
            "source": "한국관광공사_빅데이터_지역별 방문자수 (metcoRegnVisitrDDList, locgoRegnVisitrDDList)",
            "url": "https://www.data.go.kr/data/15101972/openapi.do",
            "note": "현지인·외지인 = KT, 외국인 = SK텔레콤 이동통신 기반 일자별 순방문자 추정. 광역·기초 합산 불가",
            "range": [start, end],
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
        },
        "metro": [slim(i, "areaNm") for i in metro],
        "local": [slim(i, "signguNm") for i in local],
    }, ensure_ascii=False), encoding="utf-8")
    dates = sorted({i["baseYmd"] for i in metro})
    print(f"광역 {len(metro)}행, 기초 {len(local)}행, 날짜 {dates[0] if dates else '-'} ~ {dates[-1] if dates else '-'}")


if __name__ == "__main__":
    main()
