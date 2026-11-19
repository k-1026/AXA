"""등록 유치기관 161곳 진료시간 작업표 만들기 (2026-11-18).

입력: 등록 명단 + 심평원 진료시간(10/28) + 10/28 직접 채움 2개 + 심평원 상세 재수집(11/18) + 국립중앙의료원(11/18)
     + (있으면) interim/영업정보/registered_match_candidates.csv (ykiho 없는 곳의 후보)
출력: data/interim/영업정보/registered_hours_fill.csv  (요일 칸을 공공 API 값으로 미리 채움, 사람 검증 칸 verify)
     data/processed/daegu_hours_manual.csv          (백엔드 로더용: ykiho 확정 + 새로 채운 행만, API 빈 요일 보충)
우선순위: 심평원 10/28 → 심평원 11/18 재수집 → 국립중앙의료원 → (사람이 직접)
실행: python data/etl/fetch_registered_hours.py 다음에 python data/etl/build_registered_hours.py
공개 저장소에는 합친 결과(data/processed/daegu_hours_manual.csv) 하나만 올림. 카카오·네이버 확인 원본과
중간표(interim/영업정보/kakao_*·naver_check_*·registered_hours_*·registered_match_candidates.csv)는 로컬에만 보관 (.gitignore)
"""

import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data"
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
HIRA_D = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
HIRA_URL = "https://www.data.go.kr/data/15001699/openapi.do"
NMC_URL = "https://www.data.go.kr/data/15000736/openapi.do"
CHECKED = "2026-11-18"


def rd(p):
    return list(csv.DictReader(open(D / p, encoding="utf-8-sig")))


def dg(t):
    return re.sub(r"\D", "", t or "")


def nm(s):
    return re.sub(r"[\s()（）·.\-]|의료법인|재단법인|사단법인|학교법인", "", s or "")


def hm(v):
    v = str(v if v is not None else "").strip()  # JSON 재수집본은 숫자(900)로 올 때가 있음
    if not re.fullmatch(r"\d{3,4}", v):
        return None
    v = v.zfill(4)
    return f"{v[:2]}:{v[2:]}"


def rng(a, b):
    a, b = hm(a), hm(b)
    return f"{a}-{b}" if a and b and a < b else ""


LUNCH = re.compile(r"(\d{1,2})\s*[:시]\s*(\d{2})?\s*분?\s*[~\-]\s*(\d{1,2})\s*[:시]\s*(\d{2})?")


def lunch(text):
    m = LUNCH.search(text or "")
    return f"{int(m[1]):02d}:{m[2] or '00'}-{int(m[3]):02d}:{m[4] or '00'}" if m else ""


def from_hira(h):
    return {d: rng(h.get(f"trmt{c}Start"), h.get(f"trmt{c}End")) for d, c in zip(DAYS, HIRA_D)}


def from_nmc(n):
    return {d: rng(n.get(f"dutyTime{i}s"), n.get(f"dutyTime{i}c")) for i, d in enumerate(DAYS, 1)}


reg = rd("processed/daegu_registered_institutions.csv")
hosp = {r["ykiho"]: r for r in rd("interim/영업정보/daegu_hospitals.csv")}
hrs = {r["ykiho"]: r for r in rd("interim/영업정보/daegu_hospital_hours.csv")}
man = {r["ykiho"]: r for r in rd("interim/영업정보/manual_fill_junggu_suseonggu.csv") if r["fill_status"] == "filled"}
sus = {r["ykiho"]: r for r in rd("interim/영업정보/suseong_foreign_patient_facilities.csv") if r["ykiho"] and r["weekday_hours"]}
det = json.load(open(D / "raw/영업정보/registered_hira_detail_2026-11-18.json", encoding="utf-8"))["items"]
nmc = json.load(open(D / "raw/영업정보/daegu_nmc_hospitals.json", encoding="utf-8"))["items"]
cp = D / "interim/영업정보/registered_match_candidates.csv"
cand = {r["registration_no"]: r for r in rd("interim/영업정보/registered_match_candidates.csv")} if cp.exists() else {}
vp = D / "interim/영업정보/registered_hours_verify.csv"  # 사람·브라우저 검증 결과 (일치/부분일치/불일치)
verify = {r["registration_no"]: r for r in rd("interim/영업정보/registered_hours_verify.csv")} if vp.exists() else {}


def load_kakao():
    """카카오맵 영업정보(병원이 관리하는 칸) 확인 결과 → {registration_no: {...}}.
    쓸 수 없는 경우: 정보 없음 · E-gen 제공(공공값과 같은 출처라 검증 X) · 다른 장소로 보이는 낮은 점수 · 24시간(응급실 등)."""
    tp, kp = D / "interim/영업정보/kakao_targets_2026-11-18.csv", D / "raw/영업정보/kakao_business_hours_2026-11-18.tsv"
    if not (tp.exists() and kp.exists()):
        return {}
    reg_of = {r["i"]: r["registration_no"] for r in rd("interim/영업정보/kakao_targets_2026-11-18.csv")}
    out = {}
    for line in open(kp, encoding="utf-8").read().splitlines()[1:]:
        i, pid, score, kname, dayss, note = (line.split("\t") + [""] * 6)[:6]
        parts = dayss.split(",")
        dd, lunches = {}, {}
        for d, p in zip(DAYS, parts):
            p = p.strip()
            if p == "휴무일":
                dd[d] = "휴진"
                continue
            m = re.fullmatch(r"(\d\d):(\d\d)-(\d\d):(\d\d)(?:/(\d\d:\d\d)-(\d\d:\d\d))?", p)
            ok = m and f"{m[1]}:{m[2]}" < f"{m[3]}:{m[4]}" and m[3] != "24"
            dd[d] = f"{m[1]}:{m[2]}-{m[3]}:{m[4]}" if ok else ""
            if ok and m[5]:
                lunches[d] = f"{m[5]}-{m[6]}"
        wk = [lunches[d] for d in DAYS[:5] if d in lunches]
        reason = ""
        if not pid:
            reason = "검색 결과 없음"
        elif "E-gen" in note:
            reason = "E-gen 제공(공공값과 같은 출처)"
        elif int(score or 0) < 3:
            reason = "다른 장소일 수 있음(전화·주소 불일치)"
        elif "24:00" in dayss or "응급" in kname:
            reason = "24시간/응급실 장소(외래 시간 아님)"
        elif sum(bool(dd[d]) for d in DAYS[:5]) < 3:
            reason = "영업정보 없음"
        out[reg_of.get(i, "")] = dict(usable=not reason, reason=reason, days=dd,
                                      lunch_week=max(set(wk), key=wk.count) if wk else "", lunch_sat=lunches.get("sat", ""),
                                      url=f"https://place.map.kakao.com/{pid}" if pid else "", note=note)
    return out


kakao = load_kakao()


def load_naver():
    """네이버 지도 교차확인 결과 (사람·AI가 채운 확인표) → {registration_no: {result, days, lunch, url, raw}}."""
    p = D / "interim/영업정보/naver_check_2026-11-18_result.csv"
    if not p.exists():
        return {}
    ko = dict(zip("월화수목금토일", DAYS))
    out = {}
    for r in rd("interim/영업정보/naver_check_2026-11-18_result.csv"):
        dd = {}
        for part in (r["naver_hours"] or "").split(" / "):
            m = re.match(r"\s*([월화수목금토일])(?:\([^)]*\))?\s+(\d\d:\d\d-\d\d:\d\d|휴진)\s*$", part)
            if m and (m[2] == "휴진" or m[2][:5] < m[2][6:]):
                dd[ko[m[1]]] = m[2]
        lm = re.search(r"점심: [^→]*→ 네이버 (\d\d:\d\d-\d\d:\d\d)", r["memo"] or "")
        out[r["registration_no"]] = dict(result=r["result"], days=dd, lunch=lm[1] if lm else "",
                                         url=r["naver_url"], raw=r["naver_hours"])
    return out


naver = load_naver()

by_tel, by_name = {}, {}
for n in nmc:
    for t in {dg(n.get("dutyTel1")), dg(n.get("dutyTel3"))} - {""}:
        by_tel.setdefault(t, []).append(n)
    by_name.setdefault(nm(n["dutyName"]), []).append(n)


def nmc_find(y, tel):
    h = hosp.get(y)
    if h:
        cs = [n for n in by_name.get(nm(h["yadmNm"]), [])
              if n["dutyAddr"][:9] == h["addr"][:9] or dg(n["dutyTel1"]) == dg(h["telno"])]
        if cs:
            return cs[0], "이름+주소/전화"
        cs = by_tel.get(dg(h["telno"]), [])
        if len(cs) == 1:
            return cs[0], "전화"
    cs = by_tel.get(dg(tel), [])
    return (cs[0], "등록명단 전화") if len(cs) == 1 else (None, "")


out, c = [], Counter()
for r in reg:
    y = r["ykiho"]
    cd = cand.get(r["registration_no"]) or {}
    cy = cd.get("candidate_ykiho", "")
    yk = y or cy
    h, api = hosp.get(yk), hrs.get(yk)
    row = dict(registration_no=r["registration_no"], name_ko=(h or {}).get("yadmNm", ""), name_en=r["name_en"],
               type_en=r["type_en"], gu=(h or {}).get("sgguCdNm", ""), addr=(h or {}).get("addr") or r["address_en"],
               tel=r["tel"], website=r["website"], ykiho=y, candidate_ykiho=cy, match_candidate=cd.get("match_candidate", ""),
               has_derm=(api or {}).get("has_dermatology", ""), has_ps=(api or {}).get("has_plastic_surgery", ""))
    days = {d: "" for d in DAYS}
    lw = ls = holiday = src = url = note = ""
    base = from_hira(api) if api else {d: "" for d in DAYS}
    if sum(bool(base[d]) for d in DAYS[:5]) == 5:
        status = "filled_api"
    else:
        status = None
        d2 = det.get(yk) or {}
        options = [("심평원 상세정보 재수집", HIRA_URL, from_hira(d2), lunch(d2.get("lunchWeek")),
                    lunch(d2.get("lunchSat")), d2.get("noTrmtHoli", ""), "")]
        n, how = nmc_find(yk, r["tel"])
        if n:
            hol = rng(n.get("dutyTime8s"), n.get("dutyTime8c"))
            options.append(("국립중앙의료원 병·의원 찾기", NMC_URL, from_nmc(n), lunch(n.get("dutyEtc")), "",
                            f"공휴일 {hol}" if hol else "",
                            f"NMC {n.get('hpid', '')} {n['dutyName']} (맞춘 방법: {how})"))
        # 10/28에 사람이 확인한 값이 있으면 그걸 우선 (11/18 검증: NMC가 10/28·카카오 영업정보와 7곳 중 6곳 다름)
        if y in man or y in sus:
            options = []
        for name, u, dd, l1, l2, hol, nt in options:
            if sum(bool(dd[d]) for d in DAYS[:5]) >= 3:
                days = {d: base[d] or dd[d] for d in DAYS}
                lw, ls, holiday, src, url, note = l1, l2, hol, name, u, nt
                status = "filled_hira_new" if name.startswith("심평원") else "filled_nmc"
                break
        if status is None:
            if y in man or y in sus:
                status = "filled_manual_1028"
                note = "10/28 직접 채움: " + ((man.get(y) or {}).get("weekday_hours") or sus[y]["weekday_hours"])
            elif not yk:
                status = "need_match"
            else:
                status = "need_fill"
    if not y and status.startswith("filled"):
        status += "+need_match"  # 시간은 찾았지만 ykiho 확정 필요 (후보)
    v = verify.get(r["registration_no"]) or {}
    if v.get("result") == "불일치" and status in ("filled_nmc", "filled_hira_new"):
        status = "verify_mismatch"  # 공공 API 값이 틀린 것으로 확인 → 공개 X, 사람이 홈페이지·전화로 고쳐 넣기
    grade = "공식" if src else ""
    if status.startswith("filled_api"):
        days = dict(base)
        lw = lunch((api or {}).get("lunchWeek"))
        ls = lunch((api or {}).get("lunchSat"))
    # ── 카카오맵 영업정보로 검증 (2026-11-18 전체 확인, data/raw/영업정보/kakao_business_hours_2026-11-18.tsv) ──
    override, kres = "", ""
    pub = dict(days)  # 공공값(심평원·NMC) — 카카오·네이버 비교용
    kk = kakao.get(r["registration_no"])
    if kk and not kk["usable"]:
        kres = "카카오 확인 불가: " + kk["reason"]
    elif kk:
        conflicts = [d for d in DAYS if days[d] and kk["days"][d] and days[d] != kk["days"][d]]
        compared = sum(1 for d in DAYS if days[d] and kk["days"][d])
        if status.startswith(("need", "filled_manual_1028")) or conflicts or compared < 3:
            was = " / ".join(f"{d} {days[d]}" for d in DAYS if days[d])
            kres = ("카카오와 다름 → 카카오 값으로 변경 (" + ",".join(conflicts) + ")") if conflicts else "카카오 값으로 채움"
            if status.startswith("filled_api") and conflicts:
                override = "Y"  # 심평원 API 값도 덮어써야 함 (로더 override)
            days = {d: kk["days"][d] or (days[d] if d not in conflicts else "") for d in DAYS}
            lw, ls = kk["lunch_week"] or lw, kk["lunch_sat"] or ls
            src, url, grade = "카카오맵 영업정보(병원 관리)", kk["url"], "플랫폼"
            note = (note + " | " if note else "") + ("이전 값: " + was if was else "")
            status = "filled_kakao" + ("+need_match" if not y else "")
        else:
            kres = "카카오 일치"
            for d in DAYS:  # 공공값이 빈 요일은 카카오로 보충 (예: 토요일 휴진)
                if not days[d] and kk["days"][d]:
                    days[d] = kk["days"][d]
            lw, ls = lw or kk["lunch_week"], ls or kk["lunch_sat"]
    # ── 네이버 지도 교차확인 (2026-11-18, naver_check_2026-11-18_result.csv) ──
    # 규칙(팀 결정 11/18): 카카오·네이버가 다른 요일은 공공값(심평원·NMC)으로 확인 → 공공값이 카카오와 같으면 카카오 유지,
    # 그 밖(공공값도 다르거나 없음)은 네이버 기준
    nv = naver.get(r["registration_no"])
    if nv and nv["result"] == "일치":
        kres = (kres + " · " if kres else "") + "네이버 일치"
    elif nv and nv["result"] == "다름":
        changed = []
        for d in DAYS:
            n_v = nv["days"].get(d, "")
            if not n_v or n_v == days[d]:
                continue
            if days[d] and pub[d] == days[d]:
                continue  # 공공값 = 카카오 → 출처 2개, 유지
            changed.append(d)
            days[d] = n_v
        if nv["lunch"]:
            lw = nv["lunch"]
        if changed:
            src, url, grade = "네이버 플레이스", nv["url"], "플랫폼"
            if status.startswith("filled_api") and any(base.get(d) for d in changed):
                override = "Y"
            if not status.startswith("filled_kakao"):
                status = "filled_kakao" + ("+need_match" if not y else "")
        kres = (kres + " · " if kres else "") + ("네이버 기준으로 변경(" + ",".join(changed) + ")" if changed else "네이버와 다름, 공공값=카카오라 유지")
        note = (note + " | " if note else "") + "네이버: " + nv["raw"]
    if status.startswith("filled_kakao") and any(base.get(d) and days[d] != base[d] for d in DAYS):
        override = "Y"
    row.update(status=status, **days, lunch_week=lw, lunch_sat=ls, holiday=holiday,
               source=src, source_grade=grade, source_url=url, checked_at=CHECKED if src else "",
               verify=kres or v.get("result", ""),
               verify_source=(kk or {}).get("url", "") or " ".join(filter(None, [v.get("kakao_business_hours"), v.get("verify_url")])),
               override=override, note=note)
    out.append(row)
    c[status] += 1

order = ["need_match", "need_fill", "verify_mismatch", "filled_manual_1028", "filled_kakao+need_match", "filled_nmc+need_match",
         "filled_hira_new+need_match", "filled_api+need_match", "filled_kakao", "filled_nmc", "filled_hira_new", "filled_api"]
out.sort(key=lambda x: (order.index(x["status"]) if x["status"] in order else 99, x["gu"], x["name_ko"] or x["name_en"]))
with open(D / "interim/영업정보/registered_hours_fill.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0]))
    w.writeheader()
    w.writerows(out)

load_cols = ["ykiho", *DAYS, "lunch_week", "lunch_sat", "holiday", "source_grade", "source_url", "checked_at", "override", "note"]
with open(D / "processed/daegu_hours_manual.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=load_cols)
    w.writeheader()
    for x in out:
        if not x["ykiho"] or not x["source_url"]:
            continue
        # 심평원 10/28 값 그대로인 곳은 로더가 API에서 읽음 → 카카오로 빈 요일을 보충했거나 바꾼 곳만
        if x["status"] in ("filled_nmc", "filled_hira_new", "filled_kakao") or (x["status"] == "filled_api" and x["verify"] == "카카오 일치"):
            w.writerow({k: x[k] for k in load_cols})

for k in order:
    if c[k]:
        print(f"{k:28s}{c[k]}")
print("합계", sum(c.values()))
