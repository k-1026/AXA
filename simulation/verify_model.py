"""엑셀 수식 검증 — profit_model.xlsx의 수식을 계산 엔진(formulas)으로 풀어 Python 계산(results.json)과 대조.

실행: python3 simulation/verify_model.py   (openpyxl, formulas 필요)
결과: output/verify_formulas.md
"""
import sys
from pathlib import Path

import formulas
import openpyxl

sys.path.insert(0, str(Path(__file__).parent))
import build_profit_model as b  # noqa: E402

res = b.build_results()
b.build_workbook([(s["key"], s["name"]) for s in res["sensitivity"]], res)


def solve(path):
    sol = formulas.ExcelModel().loads(str(path)).finish().calculate()
    return {k.upper(): v for k, v in sol.items()}, path.name


LK, NAME = solve(b.OUT)


def val(sheet, cell, lk=None, name=None):
    lk, name = (lk or LK), (name or NAME)
    return lk[f"'[{name}]{sheet}'!{cell}".upper()].value[0, 0]


checks, errors = [], []


def cmp(label, sheet, cell, expect, tol=0.5, lk=None, name=None):
    got = val(sheet, cell, lk, name)
    if isinstance(expect, (int, float)):
        ok = isinstance(got, (int, float)) and abs(got - expect) <= tol
    else:
        ok = got == expect
    checks.append((label, f"{sheet}!{cell}", got, expect, ok))


QS = b.QS
Lsel = b.L_SELECTED - 1
for sc in b.SC:
    run = next(r for r in res["runs"] if r["scenario"] == sc and r["L_index"] == Lsel)
    for j, q in enumerate(run["quarters"]):
        c = b.QC[j]
        cmp(f"{sc} {q['q']} 플랫폼 매출", QS, f"{c}{b.PNL[(sc, 'rev')]}", q["revenue"])
        cmp(f"{sc} {q['q']} 운영손익", QS, f"{c}{b.PNL[(sc, 'op')]}", q["op"])
        cmp(f"{sc} {q['q']} 누적 현금", "현금흐름", f"{c}{b.CF[(sc, 'cash')]}", q["cash_cum"])
    for y, col in enumerate("BCD"):
        yy = run["years"][y]
        cmp(f"{sc} {b.YN[y]} 매출 (연간손익)", "연간손익", f"{col}{b.AN[(sc, 'rev')]}", yy["revenue"])
        cmp(f"{sc} {b.YN[y]} 광고 수익 (연간손익)", "연간손익", f"{col}{b.AN[(sc, 'ad')]}", yy["ad"])
        cmp(f"{sc} {b.YN[y]} 운영손익 (연간손익)", "연간손익", f"{col}{b.AN[(sc, 'op')]}", yy["op"])
        cmp(f"{sc} {b.YN[y]} 연말 잔고 (연간손익)", "연간손익", f"{col}{b.AN[(sc, 'cash')]}", yy["cash_end"])
    s = run["summary"]
    cmp(f"{sc} 첫 흑자 연도", "연간손익", f"B{b.AN[(sc, '첫 흑자 연도')]}", s["first_profit_year"] or "3년 안에 없음")
    cmp(f"{sc} 첫 흑자 분기", "연간손익", f"B{b.AN[(sc, '첫 흑자 분기 (참고)')]}",
        b.QL[b.QN.index(s["first_profit_q"])] if s["first_profit_q"] else "3년 안에 없음")
    cmp(f"{sc} 필요 초기자금", "연간손익", f"B{b.AN[(sc, '필요 초기자금')]}", s["need_capital"])
    s1, s2, s3, s4 = b.REF["LC_cols"]
    for li in range(3):
        rr = next(r for r in res["runs"] if r["scenario"] == sc and r["L_index"] == li)["summary"]
        row = b.LC[(sc, li)]
        cmp(f"{sc} L{li+1} 3년 누적손익", "인건비비교", f"{s2}{row}", rr["op_total"])
        cmp(f"{sc} L{li+1} 최저 누적현금", "인건비비교", f"{s3}{row}", rr["min_cash"])
        cmp(f"{sc} L{li+1} 필요 초기자금", "인건비비교", f"{s4}{row}", rr["need_capital"])
        cmp(f"{sc} L{li+1} 첫 흑자 연도", "인건비비교", f"{s1}{row}", rr["first_profit_year"] or "없음")

for s in res["sensitivity"]:
    r = b.SE[s["key"]]
    cmp(f"민감도 {s['name']} −20%", "민감도", f"B{r}", s["minus"])
    cmp(f"민감도 {s['name']} +20%", "민감도", f"C{r}", s["plus"])
cmp("스트레스 거래 50% 감소", "민감도", f"B{b.SE['stress']}", res["stress"])
for li, be in enumerate(res["breakeven"]):
    cmp(f"손익분기 {be['label']} 필요 월 거래", "계단표", f"C{b.ST[f'be{li}']}", be["need"], tol=0.01)
u = res["unit_raw"]
for key, k in [("cb1", "cb"), ("cp1", "cp"), ("hb", "hb"), ("hp", "hp"), ("ltv", "ltv"), ("cac1", "cac1"), ("cac2", "cac2"), ("cac3", "cac3")]:
    cmp(f"단위경제 {key} (기준)", "단위경제", f"C{b.UE[key]}", u[k])

for key, cell in LK.items():
    try:
        v = cell.value[0, 0]
    except Exception:
        continue
    if (isinstance(v, str) and v.startswith("#")) or type(v).__name__ == "XlError":
        errors.append((key, str(v)))

# 개선방안 재현: 묶음 B의 칸을 가정 시트에서 바꿔 엑셀 수식으로 다시 계산
tmp = b.BASE / "output" / "_reproduce_comboB.xlsx"
wb = openpyxl.load_workbook(b.OUT)
ws = wb["가정"]
for j, v in enumerate(b.P2X):
    ws[f"{b.QC[j]}{b.REF['path_prem']}"] = v
ws[f"D{b.ROW['deals_basic']}"] = 0.75
ws[f"D{b.ROW['mkt']}"] = 300_000
ws[f"D{b.ROW['amt_mult']}"] = 1_000_000 / 730_000
wb.save(tmp)
LK2, NAME2 = solve(tmp)
comboB = next(x for x in res["combos"] if x["key"] == "comboB")
s1, s2, s3, s4 = b.REF["LC_cols"]
for li, y in enumerate(comboB["by_L"]):
    row = b.LC[("기준", li)]
    cmp(f"개선방안 묶음 B 재현 L{li+1} 3년 손익", "인건비비교", f"{s2}{row}", y["op_total"], lk=LK2, name=NAME2)
    cmp(f"개선방안 묶음 B 재현 L{li+1} 필요자금", "인건비비교", f"{s4}{row}", y["need"], lk=LK2, name=NAME2)
    cmp(f"개선방안 묶음 B 재현 L{li+1} 첫 흑자 연도", "인건비비교", f"{s1}{row}", y["first_year"] or "없음", lk=LK2, name=NAME2)
tmp.unlink()

ok = sum(c[4] for c in checks)
fmt = lambda v: f"{v:,.2f}" if isinstance(v, (int, float)) else str(v)
lines = ["# 엑셀 수식 검증 결과 (v3 · 3년·연 단위·인건비 주 4일)", "",
         f"- 대조 항목: {len(checks)}개 중 **{ok}개 일치** (허용 오차 0.5원, 손익분기 0.01건)",
         f"- 수식 오류 칸(#VALUE! 등): **{len(errors)}개**",
         "- 방법: `formulas` 계산 엔진으로 profit_model.xlsx 수식을 계산 → build_profit_model.py의 Python 계산과 비교", "",
         "| 항목 | 셀 | 엑셀 수식 결과 | Python 계산 | 일치 |", "|---|---|---:|---:|:-:|"]
lines += [f"| {l} | {c} | {fmt(g)} | {fmt(e)} | {'O' if k else 'X'} |" for l, c, g, e, k in checks]
if errors:
    lines += ["", "## 오류 칸", ""] + [f"- {k}: {v}" for k, v in errors[:50]]
(b.BASE / "output" / "verify_formulas.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"{ok}/{len(checks)} match, {len(errors)} error cells")
for c in checks:
    if not c[4]:
        print("MISMATCH", c)
for e in errors[:20]:
    print("ERR", e)
