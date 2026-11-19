"""KHIDI '외국인 자주 찾는 병원' 파일에서 대구 등록 유치의료기관을 뽑아 심평원 요양기관과 전화번호로 맞춘다.

입력: data/raw/유치기관/한국보건산업진흥원_외국인 자주 찾는 병원_20261109.csv (공공데이터포털 15152186)
      data/interim/영업정보/daegu_hospitals.csv
결과: data/processed/daegu_registered_institutions.csv
- 콘텐츠타입 REGISTERD_HOSPITALS, 사용여부 Y, 지역 대구만
- 전화번호 뒤 8자리가 1곳과만 같을 때 ykiho를 붙임. 못 맞춘 곳은 빈칸
"""
import csv, re, pathlib
REPO = pathlib.Path(__file__).resolve().parents[2]
SRC = REPO / "data/raw/유치기관/한국보건산업진흥원_외국인 자주 찾는 병원_20261109.csv"
OUT = REPO / "data/processed/daegu_registered_institutions.csv"
norm = lambda t: re.sub(r"\D", "", re.split(r"[/,~]", t)[0])[-8:]

tel = {}
for row in csv.DictReader(open(REPO / "data/interim/영업정보/daegu_hospitals.csv", encoding="utf-8-sig")):
    if row.get("telno"):
        tel.setdefault(norm(row["telno"]), []).append(row)

rows = []
for x in csv.DictReader(open(SRC, encoding="utf-8-sig")):
    if x["콘텐츠타입"] != "REGISTERD_HOSPITALS" or x["사용여부"] != "Y":
        continue
    if not (x["지역"].upper() == "DAEGU" or "Daegu" in x["주소1"]):
        continue
    cand = tel.get(norm(x["전화번호"]), []) if norm(x["전화번호"]) else []
    hit = cand[0] if len(cand) == 1 else None
    rows.append({
        "registration_no": x["등록수"].strip(),
        "name_en": x["병원명"].strip(),
        "type_en": x["병원구분"],
        "address_en": x["주소1"].strip(),
        "tel": x["전화번호"].strip(),
        "website": x["웹사이트 주소(url)"].strip(),
        "ykiho": hit["ykiho"] if hit else "",
        "name_ko": hit["yadmNm"] if hit else "",
        "match": "tel" if hit else "",
    })

with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
print(f"{len(rows)}곳, 매칭 {sum(1 for r in rows if r['ykiho'])}곳")
