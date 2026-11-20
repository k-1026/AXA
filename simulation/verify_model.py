"""엑셀 수식 검증 — profit_model.xlsx의 수식을 계산 엔진(formulas)으로 풀어 Python 계산(results.json)과 대조.

실행: python3 simulation/verify_model.py   (openpyxl, formulas 필요)
결과: output/verify_formulas.md
"""
import sys
from pathlib import Path

import formulas

sys.path.insert(0, str(Path(__file__).parent))
import build_profit_model as b  # noqa: E402

res = b.build_results()
b.build_workbook([(s["key"], s["name"]) for s in res["sensitivity"]], res)

xl = formulas.ExcelModel().loads(str(b.OUT)).finish()
sol = xl.calculate()
LOOKUP = {k.upper(): v for k, v in sol.items()}


def val(sheet, cell):
    key = f"'[{b.OUT.name}]{sheet}'!{cell}".upper()
    return LOOKUP[key].value[0, 0]


checks, errors = [], []


def cmp(label, sheet, cell, expect, tol=0.5):
    got = val(sheet, cell)
    ok = isinstance(got, (int, float)) and abs(got - expect) <= tol if isinstance(expect, (int, float)) else got == expect
    checks.append((label, f"{sheet}!{cell}", got, expect, ok))


Lsel = b.L_SELECTED - 1
for sc in b.SC:
    run = next(r for r in res["runs"] if r["scenario"] == sc and r["L_index"] == Lsel)
    for j, q in enumerate(run["quarters"]):
        c = b.QC[j]
        cmp(f"{sc} {q['q']} 플랫폼 매출", "손익", f"{c}{b.PNL[(sc, 'rev')]}", q["revenue"])
        cmp(f"{sc} {q['q']} 운영손익", "손익", f"{c}{b.PNL[(sc, 'op')]}", q["op"])
        cmp(f"{sc} {q['q']} 누적 현금", "현금흐름", f"{c}{b.CF[(sc, 'cash')]}", q["cash_cum"])
    cmp(f"{sc} 첫 흑자 분기", "손익", f"B{b.PNL[(sc, 'first')]}",
        b.QL[b.QN.index(run["summary"]["first_profit_q"])] if run["summary"]["first_profit_q"] else "24개월 안에 없음")
    cmp(f"{sc} 필요 초기자금", "현금흐름", f"B{b.CF[(sc, '필요 초기자금')]}", run["summary"]["need_capital"])
    for li in range(3):
        rr = next(r for r in res["runs"] if r["scenario"] == sc and r["L_index"] == li)
        row = b.LC[(sc, li)]
        cmp(f"{sc} L{li+1} 2년 누적손익", "인건비비교", f"M{row}", rr["summary"]["op_24"])
        cmp(f"{sc} L{li+1} 최저 누적현금", "인건비비교", f"N{row}", rr["summary"]["min_cash"])
        cmp(f"{sc} L{li+1} 필요 초기자금", "인건비비교", f"O{row}", rr["summary"]["need_capital"])
        cmp(f"{sc} L{li+1} 첫 흑자", "인건비비교", f"L{row}", rr["summary"]["first_profit_q"] or "없음")

for s in res["sensitivity"]:
    r = b.SE[s["key"]]
    cmp(f"민감도 {s['name']} −20%", "민감도", f"B{r}", s["minus"])
    cmp(f"민감도 {s['name']} +20%", "민감도", f"C{r}", s["plus"])
cmp("스트레스 거래 50% 감소", "민감도", f"B{b.SE['stress']}", res["stress"])
for li, be in enumerate(res["breakeven"]):
    cmp(f"손익분기 {be['label']} 필요 월 거래", "계단표", f"C{b.ST[f'be{li}']}", be["need"], tol=0.01)
u = res["unit_raw"]
for key, k in [("cb1", "cb"), ("cp1", "cp"), ("hb", "hb"), ("hp", "hp"), ("ltv", "ltv"), ("cac1", "cac1"), ("cac2", "cac2")]:
    cmp(f"단위경제 {key} (기준)", "단위경제", f"C{b.UE[key]}", u[k])

# 모든 수식 칸 오류 검사
for key, cell in sol.items():
    try:
        v = cell.value[0, 0]
    except Exception:
        continue
    if isinstance(v, str) and v.startswith("#"):
        errors.append((key, v))
    if type(v).__name__ in ("XlError",):
        errors.append((key, str(v)))

# 개선방안 재현: 묶음 B의 칸을 가정 시트에서 바꿔 엑셀 수식으로 다시 계산
import openpyxl  # noqa: E402

tmp = b.BASE / "output" / "_reproduce_comboB.xlsx"
wb = openpyxl.load_workbook(b.OUT)
ws = wb["가정"]
for j, v in enumerate(b.P2X):
    ws[f"{b.QC[j]}{b.REF['path_prem']}"] = v
ws[f"D{b.ROW['deals_basic']}"] = 0.75
ws[f"D{b.ROW['mkt']}"] = 300_000
ws[f"D{b.ROW['amt_mult']}"] = 1_000_000 / 730_000
wb.save(tmp)
sol2 = formulas.ExcelModel().loads(str(tmp)).finish().calculate()
LK2 = {k.upper(): v for k, v in sol2.items()}
comboB = next(x for x in res["combos"] if x["key"] == "comboB")
for li, y in enumerate(comboB["by_L"]):
    row = b.LC[("기준", li)]
    for col, exp, lab in (("M", y["op_24"], "2년 손익"), ("O", y["need"], "필요자금"), ("L", y["first"] or "없음", "첫 흑자")):
        got = LK2[f"'[{tmp.name}]인건비비교'!{col}{row}".upper()].value[0, 0]
        good = abs(got - exp) <= 0.5 if isinstance(exp, (int, float)) else got == exp
        checks.append((f"개선방안 묶음 B 재현 L{li+1} {lab}", f"인건비비교!{col}{row}", got, exp, good))
tmp.unlink()

ok = sum(c[4] for c in checks)
lines = [f"# 엑셀 수식 검증 결과", "",
         f"- 대조 항목: {len(checks)}개 중 **{ok}개 일치** (허용 오차 0.5원, 손익분기 0.01건)",
         f"- 수식 오류 칸(#VALUE! 등): **{len(errors)}개**",
         "- 방법: `formulas` 계산 엔진으로 profit_model.xlsx 수식을 계산 → build_profit_model.py의 Python 계산과 비교", "",
         "| 항목 | 셀 | 엑셀 수식 결과 | Python 계산 | 일치 |", "|---|---|---:|---:|:-:|"]
for label, cell, got, exp, good in checks:
    f = lambda v: f"{v:,.2f}" if isinstance(v, (int, float)) else str(v)
    lines.append(f"| {label} | {cell} | {f(got)} | {f(exp)} | {'O' if good else 'X'} |")
if errors:
    lines += ["", "## 오류 칸", ""] + [f"- {k}: {v}" for k, v in errors[:50]]
(b.BASE / "output" / "verify_formulas.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"{ok}/{len(checks)} match, {len(errors)} error cells")
for c in checks:
    if not c[4]:
        print("MISMATCH", c)
for e in errors[:20]:
    print("ERR", e)
