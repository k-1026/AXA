"""메디대구 3년 수익 시뮬레이션 (연 단위 보고, 내부는 분기 계산) — 수식이 살아 있는 xlsx + 대시보드용 results.json.

실행: python3 simulation/build_profit_model.py   (openpyxl 필요)
- 엑셀(output/profit_model.xlsx): 결과 칸은 모두 수식, 가정 시트 노란 칸을 바꾸면 따라 바뀜
  · '연간손익' = 1년 단위 결과 · '분기계산' = 병원 순차 입점을 반영하려고 3개월 단위로 계산한 바탕 시트
- results.json: 같은 계산을 Python으로 다시 해서 대시보드에 표시 (verify_model.py가 엑셀 수식 결과와 대조)
- 자료·경쟁비교 시트는 source/실습양식 엑셀에서 그대로 복사

변경 이력
- v1 (2026-11-20): 2년·8분기, 인건비 3단계(0 / 250만 / 862.8만), 적용 250만
- v2 (2026-11-20): 3년·연 단위, 팀 인건비 = 4명 × 하루 4시간(월 431.4만 원) 적용, 웹사이트 하단 광고 배너 월 15만 원 추가.
  3년차 병원 경로는 2년차 속도를 이어 67곳(프리미엄 10곳)으로 둠 (새 가정). 그 밖의 가정은 v1과 같음.
- v3 (2026-11-20): 팀 인건비를 4명 × 주 4일 × 하루 4시간(월 345.1만 원)으로 변경. 그 밖은 v2와 같음.
- v4 (2026-11-23): 구독료 없음 — 기본 13% · 프리미엄 8%, 둘 다 진료 완료·완납 건 진료비 기준 수수료만. 그 밖은 v3와 같음.
"""
import json
from copy import copy
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as CL

BASE = Path(__file__).parent
SRC = BASE / "source" / "실습양식" / "메디대구_실습양식_수익모델.xlsx"
OUT = BASE / "output" / "profit_model.xlsx"
RESULTS = BASE / "output" / "results.json"
CONCLUSIONS = BASE / "conclusions.json"

SC = ["보수", "기준", "낙관"]
SCOL = {"보수": "C", "기준": "D", "낙관": "E"}
NQ = 12
QN = [f"Q{i}" for i in range(1, NQ + 1)]
QL = [f"Q{i} ({3*i-2}~{3*i}개월)" for i in range(1, NQ + 1)]
QC = [CL(i) for i in range(2, 2 + NQ)]  # B..M
YN = ["1년차", "2년차", "3년차"]
YC = ["N", "O", "P"]   # 분기계산 시트의 연도 열
TC = "Q"               # 3년 합계 열
YR = [("B", "E"), ("F", "I"), ("J", "M")]  # 연도별 분기 열 범위
LAST = QC[-1]

# ── 팀 인건비 L: 팀 전체 월 총액 하나. 4를 곱하는 개인 급여 모델이 아님 ──
MW_HOUR = 10_320                 # 2026 최저임금 시급 (고용노동부 고시 제2025-47호)
# 주 4일 × 하루 4시간 = 주 16시간 (15시간 이상이라 주휴 3.2시간 포함 주 19.2시간)
# 월 환산: 주 40시간(주휴 포함 48시간) = 월 209시간과 같은 방식 → 19.2 ÷ 48 × 209 = 83.6시간
PART_HOURS = 83.6
L_PART = round(MW_HOUR * PART_HOURS) * 4   # 862,752 × 4 = 3,451,008
L_LEVELS = [
    (0, "0원", "참고: 팀원이 급여 없이 운영하는 경우. 사업 자체의 수익성 증거가 아님"),
    (L_PART, "월 345.1만 원", "적용: 4명 × 주 4일 × 하루 4시간(주 16시간). 2026 최저임금 시급 10,320원 × 월 83.6시간(주휴 포함) = 1인 862,752원, 팀 전체 1개 금액으로 넣음"),
    (8_627_520, "월 862.8만 원", "참고: 4명 × 하루 8시간(이전 비교값, 최저임금 월 2,156,880원 × 4)"),
]
L_SELECTED = 2  # 손익·현금흐름·민감도·계단표에 적용할 단계 (1~3)

PATH_TOTAL = [6, 12, 18, 25, 30, 35, 40, 46, 51, 56, 61, 67]
PATH_PREM = [0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# key, 항목, 단위, (보수, 기준, 낙관) 또는 수식 표시, 구분, 근거, 서식
SECTIONS = [
    ("요금·거래", [
        ("amt_mult", "거래금액 배수", "배", (0.8, 1, 1.2), "새 가정", "보수·낙관 ±20%는 검증 범위. 실측 신뢰구간 아님", "0.00"),
        ("deal_value", "평균 과금 대상 진료비 (건당)", "원", "F:deal_value", "제공문서 추정", "자료!B13 약 73만 원(환자당 지출)을 건당 금액으로 잠정 사용 × 배수. BM 문서는 1건 100만 원(50~150만) — 민감도로 확인", "#,##0"),
        ("fee_basic", "기본 수수료율", "%", (0.13, 0.13, 0.13), "팀 확정", "진료 완료·완납 건 진료비 기준 (2026-11-23 사용자 확인)", "0%"),
        ("fee_prem", "프리미엄 수수료율", "%", (0.08, 0.08, 0.08), "팀 확정", "진료 완료·완납 건 진료비 기준 (2026-11-23 사용자 확인)", "0%"),
        ("sub_fee", "프리미엄 월 이용료", "원", (0, 0, 0), "팀 확정", "v4 (2026-11-23 사용자 지시): 구독료 없음, 전부 진료비 기준 수수료. 이전 월 15만 원은 참고 시나리오로만", "#,##0"),
        ("deals_basic", "기본 병원당 월 진료 완료", "건", (0.4, 0.5, 0.6), "팀 가정", "기준 0.5 (시장규모 문서). 보수·낙관 ±20%", "0.00"),
        ("deals_prem", "프리미엄 병원당 월 진료 완료", "건", (3.2, 4, 4.8), "팀 가정", "기준 4 (시장규모 문서). 보수·낙관 ±20%", "0.00"),
        ("ad_rev", "웹사이트 하단 광고 배너 월 수익", "원", (150000, 150000, 150000), "팀 제공값", "사용자 제공(2026-11-20). 운영 1개월차부터 매월 같고 직접비 없음으로 가정. 의료광고 규제·광고주 확보는 미확인", "#,##0"),
    ]),
    ("환자 전환 (Day15 단위경제: 문의 → 예약 → 진료 완료)", [
        ("conv_book", "문의 → 상담 예약 전환율", "%", (0.15, 0.20, 0.25), "새 가정", "실측 없음. MVP 문의 로그로 교체할 첫 번째 값", "0%"),
        ("conv_done", "상담 예약 → 진료 완료 전환율", "%", (0.40, 0.50, 0.60), "새 가정", "실측 없음. 예약 후 방문·완납 비율", "0%"),
        ("inq_per_deal", "진료 완료 1건당 전체 문의 수", "건", "F:inq_per_deal", "계산", "1 ÷ (문의→예약 × 예약→완료). 미성사 문의 포함", "0.0"),
        ("repeat", "환자 1명 3년 내 이용 횟수", "회", (1, 1, 1), "새 가정", "재방문 자료 없음 → 첫 진료만 (LTV 보수적)", "0.0"),
    ]),
    ("직접 변동비", [
        ("ai_cost", "문의 1건 AI·번역 직접비", "원", (150, 100, 80), "새 가정", "기존 근거: 사후관리 AI 대화 1건 약 30원(bm 가격산정 노트). 다국어·여러 턴 상담이라 3배 이상으로 둠", "#,##0"),
        ("support", "진료 완료 1건 외주 통역·지원비", "원", (20000, 0, 0), "새 가정", "기준: 병원 코디네이터가 통역(외주 없음). 보수: 일부 외주", "#,##0"),
        ("payment", "진료 완료 1건 결제·정산·CS비", "원", (5000, 4000, 3000), "팀 가정", "기존 건당 변동비 5,000원(LLM·정산·CS) 중 LLM을 위 AI비로 분리한 나머지", "#,##0"),
        ("prem_addl", "프리미엄 병원당 월 추가 서비스비", "원", (15000, 10000, 5000), "새 가정", "대시보드 API·지원 사용량. 거래 직접비와 중복 아님", "#,##0"),
    ]),
    ("고정비·확보비", [
        ("other_fixed", "기타 월 고정비 (인건비·마케팅 제외)", "원", (210000, 210000, 210000), "팀 가정", "기존 271만 원 = 운영 인력 250만 + 호스팅 6만(확인값) + 보증보험 10만(가정) + 수작업 5만(가정). 인력 250만은 아래 L로 대체", "#,##0"),
        ("mkt", "월 환자 확보 마케팅비", "원", (500000, 500000, 500000), "새 가정", "예산은 팀 결정 사항이라 세 시나리오 동일. 결과(CAC)는 전환으로 달라짐", "#,##0"),
        ("onboard", "신규 병원 1곳 영업·온보딩 현금지출", "원", (150000, 100000, 80000), "새 가정", "방문·자료·교육 현금지출. 팀 인건비 제외 = 병원 CAC", "#,##0"),
    ]),
    ("현금흐름", [
        ("initial_out", "초기 일회성 현금지출", "원", (0, 0, 0), "미확정 (0 임시)", "구축은 팀 자체 개발 가정. 유치업 등록 자본금 1억 원은 비용이 아닌 묶이는 돈이라 제외", "#,##0"),
        ("start_cash", "초기 보유현금", "원", (0, 0, 0), "분석용", "0으로 두어 누적 부족액을 그대로 필요자금으로 읽음", "#,##0"),
        ("settle_lag", "수수료 정산 지연", "개월", (2, 1, 1), "새 가정", "진료 완납 후 다음 달 정산 가정. 구독료·광고비는 매월 수금(지연 없음)", "0"),
        ("reserve_m", "예비자금 (월 고정 지출 × 개월)", "개월", (3, 3, 3), "새 가정", "필요 초기자금 = 최대 부족액 + 예비자금", "0"),
    ]),
    ("병원 시작값", [
        ("start_basic", "개시 시점 기본 병원", "곳", (0, 0, 0), "새 가정", "0곳 출발", "0"),
        ("start_prem", "개시 시점 프리미엄 병원", "곳", (0, 0, 0), "새 가정", "0곳 출발", "0"),
    ]),
]

YELLOW = PatternFill("solid", fgColor="FFF2CC")
BLUE = PatternFill("solid", fgColor="DDEBF7")
BOLD = Font(bold=True)
TITLE = Font(bold=True, size=14)
NOTE = Font(italic=True, color="666666", size=9)

ROW, L_ROWS, REF = {}, [], {}


def A(key, sc):
    return f"'가정'!${SCOL[sc]}${ROW[key]}"


# ───────────────────────── Python 계산 (대시보드·검증용) ─────────────────────────
def params(sc):
    i = SC.index(sc)
    p = {}
    for _, items in SECTIONS:
        for key, _, _, vals, *_ in items:
            if isinstance(vals, tuple):
                p[key] = vals[i]
    p["deal_value"] = 730000 * p["amt_mult"]
    p["inq_per_deal"] = 1 / (p["conv_book"] * p["conv_done"])
    return p


def simulate(p, L):
    out, pb, pp, cum, cash, prev_fee = [], p["start_basic"], p["start_prem"], 0, p["start_cash"], 0
    lag = min(p["settle_lag"], 3)
    path_t, path_p = p.get("path_total", PATH_TOTAL), p.get("path_prem", PATH_PREM)
    for i in range(NQ):
        m = 3
        ep = path_p[i]
        eb = path_t[i] - ep
        ab, ap = (pb + eb) / 2, (pp + ep) / 2
        new = max(0, (eb + ep) - (pb + pp))
        db, dp = ab * p["deals_basic"] * m, ap * p["deals_prem"] * m
        d = db + dp
        inq = d * p["inq_per_deal"]
        gmv = d * p["deal_value"]
        fee_b = db * p["deal_value"] * p["fee_basic"]
        fee_p = dp * p["deal_value"] * p["fee_prem"]
        sub = ap * p["sub_fee"] * m
        ad = p["ad_rev"] * m
        rev = fee_b + fee_p + sub + ad
        var_deal = inq * p["ai_cost"] + d * (p["support"] + p["payment"])
        var_prem = ap * p["prem_addl"] * m
        contrib = rev - var_deal - var_prem
        fixed, mkt, onb = p["other_fixed"] * m, p["mkt"] * m, new * p["onboard"]
        pre = contrib - fixed - mkt - onb
        labor = L * m
        op = pre - labor
        cum += op
        fee = fee_b + fee_p
        cin = fee * max(0, 1 - lag / 3) + prev_fee * lag / 3 + sub + ad
        cout = var_deal + var_prem + fixed + mkt + onb + labor + (p["initial_out"] if i == 0 else 0)
        cash += cin - cout
        out.append(dict(q=QN[i], year=i // 4, basic_avg=ab, prem_avg=ap, basic_end=eb, prem_end=ep, new=new,
                        deals_basic=db, deals_prem=dp, deals=d, inquiries=inq, gmv=gmv, fee_basic=fee_b, fee_prem=fee_p,
                        sub=sub, ad=ad, revenue=rev, var_deal=var_deal, var_cost=var_deal + var_prem, contrib=contrib,
                        fixed=fixed, mkt=mkt, onboard=onb, pre_labor=pre, labor=labor,
                        total_cost=var_deal + var_prem + fixed + mkt + onb + labor,
                        op=op, op_cum=cum, cash_in=cin, cash_out=cout, cash_cum=cash))
        pb, pp, prev_fee = eb, ep, fee
    return out


SUM_KEYS = ["deals", "inquiries", "gmv", "fee_basic", "fee_prem", "sub", "ad", "revenue", "var_cost", "contrib",
            "fixed", "mkt", "onboard", "labor", "total_cost", "op"]


def yearly(qs):
    ys = []
    for y in range(3):
        part = [q for q in qs if q["year"] == y]
        d = {k: sum(q[k] for q in part) for k in SUM_KEYS}
        d.update(y=YN[y], basic_end=part[-1]["basic_end"], prem_end=part[-1]["prem_end"],
                 cash_end=part[-1]["cash_cum"], op_cum=part[-1]["op_cum"], hospitals_end=part[-1]["basic_end"] + part[-1]["prem_end"])
        ys.append(d)
    return ys


def summarize(qs, p, L):
    ys = yearly(qs)
    first_q = next((q["q"] for q in qs if q["op"] > 0), None)
    first_y = next((y["y"] for y in ys if y["op"] > 0), None)
    min_q = min(qs, key=lambda q: q["cash_cum"])
    reserve = p["reserve_m"] * (L + p["other_fixed"] + p["mkt"])
    return dict(revenue_total=sum(q["revenue"] for q in qs), op_total=sum(q["op"] for q in qs),
                first_profit_year=first_y, first_profit_q=first_q,
                min_cash=min_q["cash_cum"], min_cash_q=f"{min_q['q']} 말({YN[min_q['year']]})",
                need_capital=max(0, -min_q["cash_cum"]) + reserve, reserve=reserve,
                cash_end=qs[-1]["cash_cum"], y3_op=ys[2]["op"])


def y3_op(p, L, mods=None):
    """기준 3년차 연간 운영손익 — 한 변수씩 배수 적용 (민감도 대조용)"""
    mods = mods or {}
    p = dict(p)
    for k, m in mods.items():
        if k in p:
            p[k] = p[k] * m
    p["inq_per_deal"] = 1 / (p["conv_book"] * p["conv_done"])
    L = L * mods.get("L", 1)
    qs = simulate(p, L)[8:12]
    op = sum(q["op"] for q in qs)
    if "prem_share" in mods:
        c = p["inq_per_deal"] * p["ai_cost"] + p["support"] + p["payment"]
        prem_unit = p["deals_prem"] * 3 * (p["deal_value"] * p["fee_prem"] - c) + 3 * (p["sub_fee"] - p["prem_addl"])
        basic_unit = p["deals_basic"] * 3 * (p["deal_value"] * p["fee_basic"] - c)
        op += sum(q["prem_avg"] for q in qs) * (mods["prem_share"] - 1) * (prem_unit - basic_unit)
    return op


# ── 개선 방안: 팀이 바꿀 수 있는 것. (가정 시트에서 바꿀 칸, 바꿀 값) ──
P2X = [v * 2 if i else 0 for i, v in enumerate([0, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])]  # 0,1,2,4,…,20
P2X = [int(v) for v in P2X]
FAST = PATH_TOTAL[1:] + [PATH_TOTAL[-1] + 5]   # 한 분기 앞당김: 12,18,…,67,72
LEVERS = [
    dict(key="prem", name="프리미엄 전환 2배", change="프리미엄 병원 3년차 말 10곳 → 20곳 (전체 병원 수는 그대로)",
         how="월 4건 이상 병원에 대시보드·사후관리 가치를 보여 유료 전환. 프리미엄 1곳 공헌이익이 기본의 약 8배",
         mod={"path_prem": P2X}, cells="가정 프리미엄(기말) 경로 B~M = " + ",".join(map(str, P2X)), group="영업·운영"),
    dict(key="basic", name="기본 병원 거래 늘리기", change="기본 병원당 월 진료 완료 0.5건 → 0.75건",
         how="챗봇·다국어 페이지로 기본 병원에도 환자를 더 연결 (병원 활동률 관리)",
         mod={"deals_basic": 0.75}, cells="가정 기본 병원당 월 진료 완료 D열 = 0.75", group="영업·운영"),
    dict(key="deal", name="고단가 진료과 중심", change="건당 진료비 73만 원 → 100만 원",
         how="피부·성형·검진 등 1건 금액이 큰 진료과 병원을 먼저 입점 (BM 문서의 100만 원 추정과 같은 수준)",
         mod={"deal_value": 1_000_000}, cells="가정 거래금액 배수 D열 = 1.3699 (=100만÷73만)", group="영업·운영"),
    dict(key="fast", name="병원 확보 한 분기 앞당기기", change="입점 경로를 3개월 빠르게 (Q1 12곳 출발, 3년차 말 72곳)",
         how="개시 전에 선계약 병원을 확보해 Q1부터 12곳으로 출발",
         mod={"path_total": FAST}, cells="가정 전체 병원(기말) 경로 B~M = " + ",".join(map(str, FAST)), group="영업·운영"),
    dict(key="mkt", name="마케팅비 효율화", change="환자 마케팅비 월 50만 → 30만 원 (같은 거래량 유지 가정)",
         how="유료 광고 대신 병원 공동 콘텐츠·SNS·대만 커뮤니티 등 저비용 채널. 거래가 줄면 효과도 줄어듦",
         mod={"mkt": 300_000}, cells="가정 월 환자 확보 마케팅비 D열 = 300,000", group="비용"),
    dict(key="onb", name="온보딩 온라인화", change="신규 병원 1곳 온보딩 현금지출 10만 → 5만 원",
         how="방문 대신 화상 교육·온보딩 자료로 병원 가입 처리",
         mod={"onboard": 50_000}, cells="가정 신규 병원 1곳 영업·온보딩 D열 = 50,000", group="비용"),
    dict(key="conv", name="문의 → 예약 전환율 개선", change="문의→예약 20% → 30%",
         how="챗봇 상담 품질·가격 안내 개선. 이 모델에서는 AI비만 줄어 효과가 작음 (거래 수는 병원 수가 정함)",
         mod={"conv_book": 0.30}, cells="가정 문의→상담 예약 전환율 D열 = 30%", group="비용"),
]
REF_LEVERS = [  # 요금안은 팀 확정이라 참고만
    dict(key="sub15", name="(참고) 프리미엄 구독료 월 15만 원", change="구독료 0원 → 월 15만 원 (이전 요금안)", how="11/23 결정으로 구독료를 없앴다. 이전 요금안과 차이를 보려고 참고로만 둔다",
         mod={"sub_fee": 150_000}, cells="가정 프리미엄 월 이용료 D열 = 150,000", group="요금 (참고)"),
    dict(key="fee15", name="(참고) 기본 수수료 15%", change="13% → 15%", how="요금안 v4 변경이 필요하다. 이번 분석에서는 참고로만 본다",
         mod={"fee_basic": 0.15}, cells="가정 기본 수수료율 D열 = 15%", group="요금 (참고)"),
]
COMBOS = [
    dict(key="comboA", name="묶음 A: 영업·운영으로 바꿀 수 있는 것", change="프리미엄 2배 + 기본 0.75건 + 마케팅 30만",
         how="요금은 그대로, 팀 실행으로 바꿀 수 있는 세 가지", mod={"path_prem": P2X, "deals_basic": 0.75, "mkt": 300_000},
         cells="위 세 칸을 함께 변경", group="묶음"),
    dict(key="comboB", name="묶음 B: A + 고단가 진료과", change="묶음 A + 건당 진료비 100만 원",
         how="묶음 A에 진료과 선택까지 더함", mod={"path_prem": P2X, "deals_basic": 0.75, "mkt": 300_000, "deal_value": 1_000_000},
         cells="위 네 칸을 함께 변경", group="묶음"),
]


def lever_params(mod):
    p = params("기준")
    p.update(mod)
    p["inq_per_deal"] = 1 / (p["conv_book"] * p["conv_done"])
    return p


def lever_result(lv):
    out = {k: lv[k] for k in ("key", "name", "change", "how", "cells", "group")}
    out["by_L"] = []
    for L, lab, _ in L_LEVELS:
        b0 = summarize(simulate(params("기준"), L), params("기준"), L)
        p = lever_params(lv["mod"])
        qs = simulate(p, L)
        s = summarize(qs, p, L)
        out["by_L"].append(dict(L_label=lab, first_year=s["first_profit_year"], first_q=s["first_profit_q"],
                                op_total=s["op_total"], delta=s["op_total"] - b0["op_total"],
                                need=s["need_capital"], y3_op=s["y3_op"], years_op=[y["op"] for y in yearly(qs)]))
    return out


SENS = [
    ("L", "팀 인건비 L"), ("deal_value", "건당 진료비"), ("deals_basic", "기본 병원당 월 완료"),
    ("deals_prem", "프리미엄 병원당 월 완료"), ("prem_share", "유료 전환 (프리미엄 병원 수)"), ("mkt", "환자 마케팅비"),
    ("ad_rev", "광고 배너 수익"), ("conv_book", "문의→예약 전환율"), ("ai_cost", "문의당 AI·번역비"),
    ("payment", "건당 결제·정산·CS비"), ("onboard", "병원 온보딩비"),
]


# ───────────────────────── 엑셀 작성 ─────────────────────────
def style_header(ws, row, ncol):
    for c in range(1, ncol + 1):
        ws.cell(row=row, column=c).font = BOLD
        ws.cell(row=row, column=c).fill = BLUE


def title(ws, text, note):
    ws["A1"] = text
    ws["A1"].font = TITLE
    ws["A2"] = note
    ws["A2"].font = NOTE


def build_assumptions(wb):
    ws = wb.create_sheet("가정")
    title(ws, "가정 — 메디대구 요금안 v4 · 3년 (연 단위 보고)",
          "노란 칸 = 입력(바꾸면 모든 시트가 따라 바뀜). '새 가정'은 실측이 아닌 검증용 값. 금액은 부가세 제외.")
    for j, h in enumerate(["항목", "단위", "보수", "기준", "낙관", "구분", "근거·입력 방법"], 1):
        ws.cell(row=3, column=j, value=h)
    style_header(ws, 3, 7)
    r = 4
    for sec, items in SECTIONS:
        r += 1
        ws.cell(row=r, column=1, value=f"■ {sec}").font = BOLD
        for key, label, unit, vals, kind, note, fmt in items:
            r += 1
            ROW[key] = r
            ws.cell(row=r, column=1, value=label)
            ws.cell(row=r, column=2, value=unit)
            ws.cell(row=r, column=6, value=kind)
            ws.cell(row=r, column=7, value=note)
            for sc in SC:
                c = ws[f"{SCOL[sc]}{r}"]
                if isinstance(vals, tuple):
                    c.value = vals[SC.index(sc)]
                    c.fill = YELLOW
                elif vals == "F:deal_value":
                    c.value = f"='자료'!$B$13*{SCOL[sc]}{ROW['amt_mult']}"
                elif vals == "F:inq_per_deal":
                    c.value = f"=1/({SCOL[sc]}{ROW['conv_book']}*{SCOL[sc]}{ROW['conv_done']})"
                c.number_format = fmt
    r += 2
    ws.cell(row=r, column=1, value="■ 팀 전체 월 인건비 L — 팀 전체 총액 1개 (적용: 4명 × 주 4일 × 하루 4시간)").font = BOLD
    r += 1
    for j, h in enumerate(["단계", "", "월 금액", "", "", "구분", "설명"], 1):
        ws.cell(row=r, column=j, value=h)
    style_header(ws, r, 7)
    for i, (amt, lab, desc) in enumerate(L_LEVELS, 1):
        r += 1
        L_ROWS.append(r)
        ws.cell(row=r, column=1, value=f"{i}단계 · {lab}")
        c = ws.cell(row=r, column=3, value=amt)
        c.fill, c.number_format = YELLOW, "#,##0"
        ws.cell(row=r, column=6, value="적용" if i == L_SELECTED else "비교용")
        ws.cell(row=r, column=7, value=desc)
    r += 1
    REF["L_sel_idx"] = r
    ws.cell(row=r, column=1, value="손익·현금흐름에 적용할 단계 (1~3)")
    c = ws.cell(row=r, column=3, value=L_SELECTED)
    c.fill = YELLOW
    ws.cell(row=r, column=7, value="인건비비교 시트는 세 단계를 모두 계산")
    r += 1
    REF["L_sel"] = r
    ws.cell(row=r, column=1, value="적용 L (월)").font = BOLD
    c = ws.cell(row=r, column=3, value=f"=INDEX(C{L_ROWS[0]}:C{L_ROWS[-1]},C{REF['L_sel_idx']})")
    c.number_format = "#,##0"
    ws.cell(row=r, column=7, value="기존 월 고정비 271만 원 중 '운영 인력 250만'은 이 L로 대체, 나머지 21만은 기타 고정비 — 중복 없음")
    r += 2
    ws.cell(row=r, column=1, value="■ 분기말 병원 확보 경로 (세 시나리오 공통 · 25 / 46 / 67곳 = 각 연도 말 병원 수)").font = BOLD
    r += 1
    REF["path_hdr"] = r
    ws.cell(row=r, column=1, value="구분")
    for j, q in enumerate(QN):
        ws[f"{QC[j]}{r}"] = q
    style_header(ws, r, NQ + 1)
    for key, label, vals in (("path_total", "전체 병원 (기말)", PATH_TOTAL), ("path_prem", "프리미엄 (기말)", PATH_PREM)):
        r += 1
        REF[key] = r
        ws.cell(row=r, column=1, value=label)
        for j, v in enumerate(vals):
            c = ws[f"{QC[j]}{r}"]
            c.value, c.fill = v, YELLOW
    r += 1
    REF["path_basic"] = r
    ws.cell(row=r, column=1, value="기본 (기말)")
    for j in range(NQ):
        ws[f"{QC[j]}{r}"] = f"={QC[j]}{REF['path_total']}-{QC[j]}{REF['path_prem']}"
    r += 1
    REF["path_m"] = r
    ws.cell(row=r, column=1, value="분기 개월 수")
    for j in range(NQ):
        c = ws[f"{QC[j]}{r}"]
        c.value, c.fill = 3, YELLOW
    r += 2
    for t in ["1~2년차 경로는 v1과 같음. 3년차(Q9~Q12)는 2년차 속도(분기 +5곳, 프리미엄 +1곳)를 이어 67곳·프리미엄 10곳으로 둔 새 가정.",
              "입점 병원을 모두 활동 병원으로 봄(해지·비활동 없음). 분기 평균 병원 = (기초 + 기말) ÷ 2.",
              "보고는 1년 단위(연간손익 시트). 병원이 분기마다 늘어나는 효과를 반영하려고 계산은 분기로 한 뒤 연도별로 합산.",
              "보수·낙관은 거래 빈도·금액 ±20%, 전환율·직접비·온보딩비도 함께 움직임. 팀 인건비·광고 수익은 세 시나리오 동일."]:
        ws.cell(row=r, column=1, value=t).font = NOTE
        r += 1
    ws.column_dimensions["A"].width = 40
    for col in [CL(i) for i in range(2, 14) if CL(i) != "G"]:
        ws.column_dimensions[col].width = 12
    ws.column_dimensions["G"].width = 90
    ws.freeze_panes = "C4"


PNL_ROWS = [
    ("months", "개월 수", "0"),
    ("b_beg", "기초 기본 병원", "0.0"), ("b_end", "기말 기본 병원", "0.0"), ("b_avg", "평균 기본 병원", "0.0"),
    ("p_beg", "기초 프리미엄 병원", "0.0"), ("p_end", "기말 프리미엄 병원", "0.0"), ("p_avg", "평균 프리미엄 병원", "0.0"),
    ("new", "신규 입점 병원", "0"),
    ("d_b", "기본 진료 완료", "0.00"), ("d_p", "프리미엄 진료 완료", "0.00"), ("d", "전체 진료 완료", "0.00"),
    ("inq", "전체 문의 (미성사 포함)", "#,##0"),
    ("gmv", "진료 거래액 (병원 매출, 플랫폼 매출 아님)", "#,##0"),
    ("fee_b", "기본 수수료 매출 (13%)", "#,##0"), ("fee_p", "프리미엄 수수료 매출 (8%)", "#,##0"),
    ("sub", "구독료 매출", "#,##0"), ("ad", "광고 배너 수익", "#,##0"), ("rev", "플랫폼 매출", "#,##0"),
    ("var_deal", "거래 연동 직접비 (문의 AI·지원·결제)", "#,##0"), ("var_prem", "프리미엄 병원 추가 서비스비", "#,##0"),
    ("contrib", "공헌이익", "#,##0"),
    ("fixed", "기타 고정비", "#,##0"), ("mkt", "환자 마케팅비", "#,##0"), ("onb", "병원 영업·온보딩비", "#,##0"),
    ("pre", "인건비 차감 전 손익", "#,##0"), ("labor", "팀 인건비 (적용 L × 개월)", "#,##0"),
    ("op", "운영손익", "#,##0"), ("cum", "누적 운영손익", "#,##0"), ("flag", "흑자 (1=흑자)", "0"),
]
STOCK = {"b_beg": "beg", "p_beg": "beg", "b_end": "end", "p_end": "end", "b_avg": "avg", "p_avg": "avg", "cum": "end"}
PNL, BLOCK_HDR = {}, {}
QS = "분기계산"


def build_quarterly(wb):
    ws = wb.create_sheet(QS)
    title(ws, "분기계산 — 3년·12분기 바탕 계산 (보수·기준·낙관) · 연도 합계는 N~P열",
          "연간손익 시트가 이 시트의 연도 열(N·O·P)을 읽음. 병원이 분기마다 늘어나는 효과를 반영하려고 3개월 단위로 계산. 모든 칸이 수식.")
    r = 3
    for sc in SC:
        BLOCK_HDR[sc] = r
        ws.cell(row=r, column=1, value=f"{sc} 시나리오")
        for j in range(NQ):
            ws[f"{QC[j]}{r}"] = QL[j]
        for col, y in zip(YC, YN):
            ws[f"{col}{r}"] = y
        ws[f"{TC}{r}"] = "3년 합계"
        style_header(ws, r, 17)
        for key, _, _ in PNL_ROWS:
            r += 1
            PNL[(sc, key)] = r
        R = lambda k: PNL[(sc, k)]
        for key, name, fmt in PNL_ROWS:
            row = R(key)
            ws.cell(row=row, column=1, value=name)
            for j, c in enumerate(QC):
                prev = QC[j - 1] if j else None
                f = {
                    "months": f"='가정'!{c}${REF['path_m']}",
                    "b_beg": f"={A('start_basic', sc)}" if j == 0 else f"={prev}{R('b_end')}",
                    "b_end": f"='가정'!{c}${REF['path_basic']}",
                    "b_avg": f"=({c}{R('b_beg')}+{c}{R('b_end')})/2",
                    "p_beg": f"={A('start_prem', sc)}" if j == 0 else f"={prev}{R('p_end')}",
                    "p_end": f"='가정'!{c}${REF['path_prem']}",
                    "p_avg": f"=({c}{R('p_beg')}+{c}{R('p_end')})/2",
                    "new": f"=MAX(0,({c}{R('b_end')}+{c}{R('p_end')})-({c}{R('b_beg')}+{c}{R('p_beg')}))",
                    "d_b": f"={c}{R('b_avg')}*{A('deals_basic', sc)}*{c}{R('months')}",
                    "d_p": f"={c}{R('p_avg')}*{A('deals_prem', sc)}*{c}{R('months')}",
                    "d": f"={c}{R('d_b')}+{c}{R('d_p')}",
                    "inq": f"={c}{R('d')}*{A('inq_per_deal', sc)}",
                    "gmv": f"={c}{R('d')}*{A('deal_value', sc)}",
                    "fee_b": f"={c}{R('d_b')}*{A('deal_value', sc)}*{A('fee_basic', sc)}",
                    "fee_p": f"={c}{R('d_p')}*{A('deal_value', sc)}*{A('fee_prem', sc)}",
                    "sub": f"={c}{R('p_avg')}*{A('sub_fee', sc)}*{c}{R('months')}",
                    "ad": f"={A('ad_rev', sc)}*{c}{R('months')}",
                    "rev": f"={c}{R('fee_b')}+{c}{R('fee_p')}+{c}{R('sub')}+{c}{R('ad')}",
                    "var_deal": f"={c}{R('inq')}*{A('ai_cost', sc)}+{c}{R('d')}*({A('support', sc)}+{A('payment', sc)})",
                    "var_prem": f"={c}{R('p_avg')}*{A('prem_addl', sc)}*{c}{R('months')}",
                    "contrib": f"={c}{R('rev')}-{c}{R('var_deal')}-{c}{R('var_prem')}",
                    "fixed": f"={A('other_fixed', sc)}*{c}{R('months')}",
                    "mkt": f"={A('mkt', sc)}*{c}{R('months')}",
                    "onb": f"={c}{R('new')}*{A('onboard', sc)}",
                    "pre": f"={c}{R('contrib')}-{c}{R('fixed')}-{c}{R('mkt')}-{c}{R('onb')}",
                    "labor": f"='가정'!$C${REF['L_sel']}*{c}{R('months')}",
                    "op": f"={c}{R('pre')}-{c}{R('labor')}",
                    "cum": f"={c}{R('op')}" if j == 0 else f"={prev}{R('cum')}+{c}{R('op')}",
                    "flag": f"=IF({c}{R('op')}>0,1,0)",
                }[key]
                ws[f"{c}{row}"] = f
                ws[f"{c}{row}"].number_format = fmt
            kind = STOCK.get(key)
            if key == "flag":
                for col in YC:
                    ws[f"{col}{row}"] = f"=IF({col}{R('op')}>0,1,0)"
                continue
            for (a, b), col in zip(YR, YC):
                ws[f"{col}{row}"] = {"beg": f"={a}{row}", "end": f"={b}{row}", "avg": f"=AVERAGE({a}{row}:{b}{row})"}.get(
                    kind, f"=SUM({a}{row}:{b}{row})")
                ws[f"{col}{row}"].number_format = fmt
            ws[f"{TC}{row}"] = {"beg": f"=B{row}", "end": f"={LAST}{row}", "avg": f"=AVERAGE(B{row}:{LAST}{row})"}.get(
                kind, f"=SUM(B{row}:{LAST}{row})")
            ws[f"{TC}{row}"].number_format = fmt
            if key in ("rev", "contrib", "op"):
                for col in ["A"] + QC + YC + [TC]:
                    ws[f"{col}{row}"].font = BOLD
        flag = R("flag")
        r += 1
        ws.cell(row=r, column=1, value="첫 흑자 분기")
        ws.cell(row=r, column=2, value=f'=IFERROR(INDEX($B${BLOCK_HDR[sc]}:${LAST}${BLOCK_HDR[sc]},MATCH(1,B{flag}:{LAST}{flag},0)),"3년 안에 없음")')
        PNL[(sc, "first_q")] = r
        r += 1
        ws.cell(row=r, column=1, value="첫 흑자 연도")
        ws.cell(row=r, column=2, value=f'=IFERROR(INDEX($N${BLOCK_HDR[sc]}:$P${BLOCK_HDR[sc]},MATCH(1,N{flag}:P{flag},0)),"3년 안에 없음")')
        PNL[(sc, "first_y")] = r
        r += 2
    ws.column_dimensions["A"].width = 38
    for c in QC + YC + [TC]:
        ws.column_dimensions[c].width = 14
    ws.freeze_panes = "B4"


CF_ROWS = [("fee", "수수료 매출 (발생 기준)"), ("cin_now", "당분기 수금 수수료"), ("cin_prev", "전분기 이월 수금 수수료"),
           ("cin_sub", "구독료 수금 (매월)"), ("cin_ad", "광고 배너 수금 (매월)"), ("cin", "현금 유입"),
           ("cout", "현금 지출 (직접비·고정비·마케팅·온보딩·인건비·초기)"),
           ("net", "순현금흐름"), ("net_pre", "인건비 차감 전 순현금흐름"), ("cash", "누적 현금 잔액")]
CF = {}


def build_cashflow(wb):
    ws = wb.create_sheet("현금흐름")
    title(ws, "현금흐름 — 누적 잔액·최대 부족액·필요 초기자금 (분기 계산, 연말 잔고는 연간손익 시트)",
          "수수료는 정산 지연만큼 다음 분기로 넘어가 수금. 구독료·광고비는 매월 수금. 부가세·세금·금융비용 제외.")
    r = 3
    for sc in SC:
        hdr = r
        ws.cell(row=r, column=1, value=f"{sc} 시나리오 (적용 L)")
        for j in range(NQ):
            ws[f"{QC[j]}{r}"] = QL[j]
        ws[f"N{r}"] = "3년 합계"
        style_header(ws, r, 14)
        for key, _ in CF_ROWS:
            r += 1
            CF[(sc, key)] = r
        P = lambda k: PNL[(sc, k)]
        R = lambda k: CF[(sc, k)]
        lag = f"MIN({A('settle_lag', sc)},3)"
        for key, name in CF_ROWS:
            row = R(key)
            ws.cell(row=row, column=1, value=name)
            for j, c in enumerate(QC):
                prev = QC[j - 1] if j else None
                q = lambda k: f"'{QS}'!{c}{P(k)}"
                f = {
                    "fee": f"={q('fee_b')}+{q('fee_p')}",
                    "cin_now": f"={c}{R('fee')}*MAX(0,1-{lag}/3)",
                    "cin_prev": "=0" if j == 0 else f"={prev}{R('fee')}*{lag}/3",
                    "cin_sub": f"={q('sub')}",
                    "cin_ad": f"={q('ad')}",
                    "cin": f"={c}{R('cin_now')}+{c}{R('cin_prev')}+{c}{R('cin_sub')}+{c}{R('cin_ad')}",
                    "cout": (f"={q('var_deal')}+{q('var_prem')}+{q('fixed')}+{q('mkt')}+{q('onb')}+{q('labor')}"
                             + (f"+{A('initial_out', sc)}" if j == 0 else "")),
                    "net": f"={c}{R('cin')}-{c}{R('cout')}",
                    "net_pre": f"={c}{R('net')}+{q('labor')}",
                    "cash": f"={A('start_cash', sc)}+{c}{R('net')}" if j == 0 else f"={prev}{R('cash')}+{c}{R('net')}",
                }[key]
                ws[f"{c}{row}"] = f
                ws[f"{c}{row}"].number_format = "#,##0"
            if key != "cash":
                ws[f"N{row}"] = f"=SUM(B{row}:{LAST}{row})"
                ws[f"N{row}"].number_format = "#,##0"
        cash = R("cash")
        rng = f"B{cash}:{LAST}{cash}"
        for label, f in (("최저 누적 현금 (최대 부족액)", f"=MIN({rng})"),
                         ("최저 시점", f"=INDEX($B${hdr}:${LAST}${hdr},MATCH(MIN({rng}),{rng},0))"),
                         ("예비자금", f"={A('reserve_m', sc)}*('가정'!$C${REF['L_sel']}+{A('other_fixed', sc)}+{A('mkt', sc)})"),
                         ("필요 초기자금", None)):
            r += 1
            ws.cell(row=r, column=1, value=label).font = BOLD
            CF[(sc, label)] = r
            if f is None:
                f = f"=MAX(0,-B{CF[(sc, '최저 누적 현금 (최대 부족액)')]})+B{CF[(sc, '예비자금')]}"
            ws.cell(row=r, column=2, value=f).number_format = "#,##0"
        r += 2
    ws.column_dimensions["A"].width = 48
    for c in QC + ["N"]:
        ws.column_dimensions[c].width = 14
    ws.freeze_panes = "B4"


AN = {}  # (sc, key) -> 연간손익 행
AN_ROWS = [
    ("hosp_end", "연말 입점 병원 (기본 + 프리미엄)", "0"), ("p_end", "  그중 프리미엄", "0"),
    ("d", "진료 완료 (건)", "#,##0.0"), ("gmv", "진료 거래액 (병원 매출, 참고)", "#,##0"),
    ("fee_b", "기본 수수료 매출", "#,##0"), ("fee_p", "프리미엄 수수료 매출", "#,##0"), ("sub", "구독료 매출", "#,##0"),
    ("ad", "광고 배너 수익", "#,##0"), ("rev", "플랫폼 매출 합계", "#,##0"),
    ("var", "직접 변동비", "#,##0"), ("contrib", "공헌이익", "#,##0"),
    ("labor", "팀 인건비", "#,##0"), ("fixed", "기타 고정비", "#,##0"), ("mkt", "환자 마케팅비", "#,##0"), ("onb", "병원 온보딩비", "#,##0"),
    ("op", "연간 운영손익", "#,##0"), ("cum", "누적 운영손익 (연말)", "#,##0"), ("cash", "연말 통장 잔고 (초기자금 0원 기준)", "#,##0"),
]


def build_annual(wb):
    ws = wb.create_sheet("연간손익")
    title(ws, "연간손익 — 3년, 1년 단위 결과 (보수·기준·낙관, 적용 L)",
          "분기계산·현금흐름 시트를 연도별로 모은 결과. 인건비 = 4명 × 주 4일 × 하루 4시간(가정 시트 적용 L). 광고 배너 월 15만 원 포함.")
    r = 3
    for sc in SC:
        ws.cell(row=r, column=1, value=f"{sc} 시나리오")
        for j, h in enumerate(YN + ["3년 합계"], 2):
            ws.cell(row=r, column=j, value=h)
        style_header(ws, r, 5)
        P = lambda k: PNL[(sc, k)]
        for key, name, fmt in AN_ROWS:
            r += 1
            AN[(sc, key)] = r
            ws.cell(row=r, column=1, value=name)
            for j, (col, (a, b)) in enumerate(zip(YC + [TC], YR + [("B", LAST)])):
                tgt = CL(2 + j)
                if key == "hosp_end":
                    f = f"='{QS}'!{col}{P('b_end')}+'{QS}'!{col}{P('p_end')}"
                elif key == "var":
                    f = f"='{QS}'!{col}{P('var_deal')}+'{QS}'!{col}{P('var_prem')}"
                elif key == "cash":
                    f = f"='현금흐름'!{b}{CF[(sc, 'cash')]}"
                else:
                    f = f"='{QS}'!{col}{P(key)}"
                ws[f"{tgt}{r}"] = f
                ws[f"{tgt}{r}"].number_format = fmt
            if key in ("rev", "op"):
                for col in "ABCDE":
                    ws[f"{col}{r}"].font = BOLD
        for label, f in (("첫 흑자 연도", f"='{QS}'!B{P('first_y')}"), ("첫 흑자 분기 (참고)", f"='{QS}'!B{P('first_q')}"),
                         ("필요 초기자금", f"='현금흐름'!B{CF[(sc, '필요 초기자금')]}"),
                         ("최대 부족 시점", f"='현금흐름'!B{CF[(sc, '최저 시점')]}")):
            r += 1
            AN[(sc, label)] = r
            ws.cell(row=r, column=1, value=label).font = BOLD
            c = ws.cell(row=r, column=2, value=f)
            c.number_format = "#,##0"
            c.font = BOLD
        r += 2
    ws.column_dimensions["A"].width = 40
    for c in "BCDE":
        ws.column_dimensions[c].width = 16
    ws.freeze_panes = "B4"


LC = {}


def build_labor_compare(wb):
    ws = wb.create_sheet("인건비비교")
    title(ws, "인건비비교 — 시나리오 3 × 팀 인건비 L 3단계 (적용 = 4명 × 주 4일 × 하루 4시간)",
          "인건비 차감 전 손익·현금에서 각 L을 빼서 계산. L을 낮춰 생긴 흑자는 사업 수익성 개선이 아니라 비용 책정 조건의 결과.")
    qcols = [CL(i) for i in range(4, 4 + NQ)]          # D..O
    ycols = [CL(i) for i in range(4 + NQ, 7 + NQ)]     # P,Q,R
    scol = [CL(i) for i in range(7 + NQ, 11 + NQ)]     # S,T,U,V
    hdr = ["시나리오", "L 단계", "월 L"] + QN + YN + ["첫 흑자 연도", "3년 누적손익", "최저 누적현금", "필요 초기자금"]
    for j, h in enumerate(hdr, 1):
        ws.cell(row=3, column=j, value=h)
    style_header(ws, 3, len(hdr))
    r = 3
    for sc in SC:
        for li, lrow in enumerate(L_ROWS):
            r += 1
            op_r = r
            ws.cell(row=r, column=1, value=sc)
            ws.cell(row=r, column=2, value=f"{li+1}단계 · {L_LEVELS[li][1]} · 운영손익")
            ws.cell(row=r, column=3, value=f"='가정'!$C${lrow}").number_format = "#,##0"
            for j, c in enumerate(qcols):
                pc = QC[j]
                ws[f"{c}{r}"] = f"='{QS}'!{pc}{PNL[(sc, 'pre')]}-$C{r}*'{QS}'!{pc}{PNL[(sc, 'months')]}"
                ws[f"{c}{r}"].number_format = "#,##0"
            for y, c in enumerate(ycols):
                a, b = qcols[4 * y], qcols[4 * y + 3]
                ws[f"{c}{r}"] = f"=SUM({a}{r}:{b}{r})"
                ws[f"{c}{r}"].number_format = "#,##0"
            r += 1
            flag_r = r
            ws.cell(row=r, column=2, value="흑자 연도 (1=흑자)")
            for c in ycols:
                ws[f"{c}{r}"] = f"=IF({c}{op_r}>0,1,0)"
            r += 1
            cash_r = r
            ws.cell(row=r, column=2, value="누적 현금 잔액")
            for j, c in enumerate(qcols):
                pc = QC[j]
                net = f"('현금흐름'!{pc}{CF[(sc, 'net_pre')]}-$C{op_r}*'{QS}'!{pc}{PNL[(sc, 'months')]})"
                ws[f"{c}{r}"] = f"={A('start_cash', sc)}+{net}" if j == 0 else f"={qcols[j-1]}{r}+{net}"
                ws[f"{c}{r}"].number_format = "#,##0"
            s1, s2, s3, s4 = scol
            ws[f"{s1}{op_r}"] = f'=IFERROR(INDEX(${ycols[0]}$3:${ycols[-1]}$3,MATCH(1,{ycols[0]}{flag_r}:{ycols[-1]}{flag_r},0)),"없음")'
            ws[f"{s2}{op_r}"] = f"=SUM({qcols[0]}{op_r}:{qcols[-1]}{op_r})"
            ws[f"{s3}{op_r}"] = f"=MIN({qcols[0]}{cash_r}:{qcols[-1]}{cash_r})"
            ws[f"{s4}{op_r}"] = f"=MAX(0,-{s3}{op_r})+{A('reserve_m', sc)}*($C{op_r}+{A('other_fixed', sc)}+{A('mkt', sc)})"
            for col in (s2, s3, s4):
                ws[f"{col}{op_r}"].number_format = "#,##0"
                ws[f"{col}{op_r}"].font = BOLD
            LC[(sc, li)] = op_r
    REF["LC_cols"] = scol
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 36
    for i in range(3, 12 + NQ):
        ws.column_dimensions[CL(i)].width = 13
    ws.freeze_panes = "D4"


UE = {}


def build_unit(wb):
    ws = wb.create_sheet("단위경제")
    title(ws, "단위경제 — 거래 1건 · 병원 1곳 · 환자 1명",
          "Day15 4교시 구조: 객단가 → 전환율 → CAC → 공헌이익 → LTV/CAC. 팀 인건비·고정비·광고 수익은 여기에 배부하지 않음.")
    for j, h in enumerate(["항목"] + SC + ["계산"], 1):
        ws.cell(row=3, column=j, value=h)
    style_header(ws, 3, 5)
    cols = {"보수": "B", "기준": "C", "낙관": "D"}

    def P(sc, k, col):
        return f"'{QS}'!{col}{PNL[(sc, k)]}"

    rows = [
        ("■ 거래 1건", None, None, None),
        ("deal", "건당 진료비 (객단가)", lambda sc: f"={A('deal_value', sc)}", "#,##0"),
        ("fee_b1", "기본 건당 수수료", lambda sc: f"={A('deal_value', sc)}*{A('fee_basic', sc)}", "#,##0"),
        ("fee_p1", "프리미엄 건당 수수료", lambda sc: f"={A('deal_value', sc)}*{A('fee_prem', sc)}", "#,##0"),
        ("inq1", "완료 1건당 문의 수", lambda sc: f"={A('inq_per_deal', sc)}", "0.0"),
        ("ai1", "완료 1건당 문의 AI·번역비", lambda sc: f"={A('inq_per_deal', sc)}*{A('ai_cost', sc)}", "#,##0"),
        ("cost1", "완료 1건당 직접비 합계", lambda sc: f"={{c}}{{ai1}}+{A('support', sc)}+{A('payment', sc)}", "#,##0"),
        ("cb1", "기본 건당 공헌이익", lambda sc: "={c}{fee_b1}-{c}{cost1}", "#,##0"),
        ("cp1", "프리미엄 건당 공헌이익", lambda sc: "={c}{fee_p1}-{c}{cost1}", "#,##0"),
        ("■ 병원 1곳 · 월", None, None, None),
        ("hb", "기본 병원 월 공헌이익", lambda sc: f"={{c}}{{cb1}}*{A('deals_basic', sc)}", "#,##0"),
        ("hp", "프리미엄 병원 월 공헌이익 (구독 포함)", lambda sc: f"={{c}}{{cp1}}*{A('deals_prem', sc)}+{A('sub_fee', sc)}-{A('prem_addl', sc)}", "#,##0"),
        ("hcac", "병원 CAC (신규 1곳 온보딩 현금지출)", lambda sc: f"={A('onboard', sc)}", "#,##0"),
        ("hpay_b", "기본 병원 CAC 회수기간 (개월)", lambda sc: '=IF({c}{hb}>0,{c}{hcac}/{c}{hb},"회수 불가")', "0.0"),
        ("hpay_p", "프리미엄 병원 CAC 회수기간 (개월)", lambda sc: '=IF({c}{hp}>0,{c}{hcac}/{c}{hp},"회수 불가")', "0.0"),
        ("even_amt", "두 요금제 병원 부담이 같은 월 거래액", lambda sc: f"={A('sub_fee', sc)}/({A('fee_basic', sc)}-{A('fee_prem', sc)})", "#,##0"),
        ("even_n", "같은 부담 월 거래 건수", lambda sc: "={c}{even_amt}/{c}{deal}", "0.00"),
        ("■ 환자 · 전환과 CAC", None, None, None),
        ("cv1", "문의 → 예약", lambda sc: f"={A('conv_book', sc)}", "0%"),
        ("cv2", "예약 → 진료 완료", lambda sc: f"={A('conv_done', sc)}", "0%"),
        ("cv", "문의 → 진료 완료", lambda sc: "={c}{cv1}*{c}{cv2}", "0.0%"),
        ("inq36", "3년 전체 문의", lambda sc: f"={P(sc, 'inq', TC)}", "#,##0"),
        ("d36", "3년 진료 완료 (= 신규 환자, 재방문 없음 가정)", lambda sc: f"={P(sc, 'd', TC)}", "#,##0.0"),
        ("cac1", "환자 CAC · 1년차 (마케팅비 ÷ 완료)", lambda sc: f"={P(sc, 'mkt', 'N')}/{P(sc, 'd', 'N')}", "#,##0"),
        ("cac2", "환자 CAC · 2년차", lambda sc: f"={P(sc, 'mkt', 'O')}/{P(sc, 'd', 'O')}", "#,##0"),
        ("cac3", "환자 CAC · 3년차", lambda sc: f"={P(sc, 'mkt', 'P')}/{P(sc, 'd', 'P')}", "#,##0"),
        ("cpa_inq", "문의 1건 획득비 · 3년 (마케팅비 ÷ 문의)", lambda sc: f"={P(sc, 'mkt', TC)}/{P(sc, 'inq', TC)}", "#,##0"),
        ("avg_c", "환자 1명 거래 공헌이익 · 3년 가중평균", lambda sc: f"=({P(sc, 'fee_b', TC)}+{P(sc, 'fee_p', TC)}-{P(sc, 'var_deal', TC)})/{P(sc, 'd', TC)}", "#,##0"),
        ("ltv", "환자 LTV (= 가중평균 공헌 × 이용 횟수)", lambda sc: f"={{c}}{{avg_c}}*{A('repeat', sc)}", "#,##0"),
        ("ltvcac1", "LTV / CAC · 1년차", lambda sc: "={c}{ltv}/{c}{cac1}", "0.00"),
        ("ltvcac2", "LTV / CAC · 2년차", lambda sc: "={c}{ltv}/{c}{cac2}", "0.00"),
        ("ltvcac3", "LTV / CAC · 3년차", lambda sc: "={c}{ltv}/{c}{cac3}", "0.00"),
    ]
    r = 3
    for key, name, fn, fmt in rows:
        r += 1
        if fn is None:
            ws.cell(row=r, column=1, value=key).font = BOLD
            continue
        UE[key] = r
        ws.cell(row=r, column=1, value=name)
        for sc in SC:
            c = cols[sc]
            ws[f"{c}{r}"] = fn(sc).format(c=c, **UE)
            ws[f"{c}{r}"].number_format = fmt
    r += 2
    for t in ["LTV는 재방문 자료가 없어 이용 1회로 둠. 비교기업 매출로 LTV를 추정하지 않음(계획 7절).",
              "LTV/CAC 3배는 업계 경험칙일 뿐 판단 기준으로 확정하지 않음(Day15 18쪽). 비율만 계산.",
              "병원 CAC는 현금지출만. 영업에 쓰는 팀 시간은 팀 인건비 L에 이미 있어 다시 넣지 않음."]:
        ws.cell(row=r, column=1, value=t).font = NOTE
        r += 1
    ws.column_dimensions["A"].width = 46
    for c in "BCD":
        ws.column_dimensions[c].width = 16


ST = {}
MULTS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3]


def build_steps(wb):
    ws = wb.create_sheet("계단표")
    title(ws, "계단표 — 3년차 마지막 분기(Q12) 기준, 월 거래량을 바꿀 때 월 손익과 손익분기",
          "Q12의 평균 병원 수·구독·광고·고정비·온보딩비를 고정하고 진료 완료 건수만 배수로 바꿈. 처리 능력 확대에 따른 추가 고정비는 반영 안 함.")
    s = "기준"
    P = lambda k: f"'{QS}'!${LAST}${PNL[(s, k)]}"
    r = 4
    items = [
        ("D", "Q12 기대 월 진료 완료", f"={P('d')}/3", "0.0"),
        ("V", "거래량 배수 1당 월 거래 공헌 (수수료 − 거래 직접비)", f"=({P('fee_b')}+{P('fee_p')}-{P('var_deal')})/3", "#,##0"),
        ("F0", "월 고정 부분 (인건비 제외: 구독 + 광고 − 추가비 − 기타고정 − 마케팅 − 온보딩)",
         f"=({P('sub')}+{P('ad')}-{P('var_prem')}-{P('fixed')}-{P('mkt')}-{P('onb')})/3", "#,##0"),
        ("Lsel", "적용 L (월)", f"='가정'!$C${REF['L_sel']}", "#,##0"),
    ]
    for key, name, f, fmt in items:
        ST[key] = r
        ws.cell(row=r, column=1, value=name)
        ws.cell(row=r, column=2, value=f).number_format = fmt
        r += 1
    r += 1
    for j, h in enumerate(["거래량 배수", "월 진료 완료", "월 플랫폼 매출", "월 총비용", "월 운영손익 (적용 L)"], 1):
        ws.cell(row=r, column=j, value=h)
    style_header(ws, r, 5)
    for m in MULTS:
        r += 1
        ws.cell(row=r, column=1, value=m).number_format = "0.00"
        ws.cell(row=r, column=1).fill = YELLOW
        ws.cell(row=r, column=2, value=f"=A{r}*$B${ST['D']}").number_format = "0.0"
        ws.cell(row=r, column=3, value=f"=(A{r}*({P('fee_b')}+{P('fee_p')})+{P('sub')}+{P('ad')})/3").number_format = "#,##0"
        ws.cell(row=r, column=5, value=f"=A{r}*$B${ST['V']}+$B${ST['F0']}-$B${ST['Lsel']}").number_format = "#,##0"
        ws.cell(row=r, column=4, value=f"=C{r}-E{r}").number_format = "#,##0"
    r += 2
    for j, h in enumerate(["손익분기 (인건비 단계별)", "월 L", "필요 월 진료 완료", "Q12 기대 대비 배수", "필요 평균 병원 수 (같은 구성비)"], 1):
        ws.cell(row=r, column=j, value=h)
    style_header(ws, r, 5)
    total_avg = f"('{QS}'!${LAST}${PNL[(s, 'b_avg')]}+'{QS}'!${LAST}${PNL[(s, 'p_avg')]})"
    for li, lrow in enumerate(L_ROWS):
        r += 1
        ST[f"be{li}"] = r
        ws.cell(row=r, column=1, value=f"{li+1}단계 · {L_LEVELS[li][1]}")
        ws.cell(row=r, column=2, value=f"='가정'!$C${lrow}").number_format = "#,##0"
        ws.cell(row=r, column=4, value=f"=MAX(0,(B{r}-$B${ST['F0']})/$B${ST['V']})").number_format = "0.00"
        ws.cell(row=r, column=3, value=f"=D{r}*$B${ST['D']}").number_format = "0.0"
        ws.cell(row=r, column=5, value=f"=D{r}*{total_avg}").number_format = "0.0"
    r += 2
    ws.cell(row=r, column=1, value="필요 평균 병원 수는 구독·프리미엄 비중이 같다고 둔 근사. 대구 등록 유치기관 161곳(자료 B10)과 비교해 현실성 확인.").font = NOTE
    ws.column_dimensions["A"].width = 62
    for c in "BCDE":
        ws.column_dimensions[c].width = 20


SE = {}


def sens_formula(key, m):
    """기준 3년차 연간 운영손익을 변수 key에 배수 m을 곱해 다시 계산하는 수식 (분기계산 P열 = 3년차 합계)"""
    s, Y = "기준", "P"
    P = lambda k: f"'{QS}'!${Y}${PNL[(s, k)]}"
    a = lambda k: A(k, s)
    base = P("op")
    c_deal = f"({a('inq_per_deal')}*{a('ai_cost')}+{a('support')}+{a('payment')})"
    if key == "L":
        return f"={base}+'가정'!$C${REF['L_sel']}*{P('months')}*(1-{m})"
    if key == "deal_value":
        return f"={base}+({P('fee_b')}+{P('fee_p')})*({m}-1)"
    if key == "deals_basic":
        return f"={base}+({P('fee_b')}-{P('d_b')}*{c_deal})*({m}-1)"
    if key == "deals_prem":
        return f"={base}+({P('fee_p')}-{P('d_p')}*{c_deal})*({m}-1)"
    if key == "mkt":
        return f"={base}-{P('mkt')}*({m}-1)"
    if key == "ad_rev":
        return f"={base}+{P('ad')}*({m}-1)"
    if key == "conv_book":
        return f"={base}-{P('d')}*{a('inq_per_deal')}*{a('ai_cost')}*(1/{m}-1)"
    if key == "ai_cost":
        return f"={base}-{P('inq')}*{a('ai_cost')}*({m}-1)"
    if key == "payment":
        return f"={base}-{P('d')}*{a('payment')}*({m}-1)"
    if key == "onboard":
        return f"={base}-{P('onb')}*({m}-1)"
    if key == "prem_share":
        prem_unit = f"({a('deals_prem')}*3*({a('deal_value')}*{a('fee_prem')}-{c_deal})+3*({a('sub_fee')}-{a('prem_addl')}))"
        basic_unit = f"({a('deals_basic')}*3*({a('deal_value')}*{a('fee_basic')}-{c_deal}))"
        return f"={base}+4*{P('p_avg')}*({m}-1)*({prem_unit}-{basic_unit})"
    raise KeyError(key)


def build_sensitivity(wb, order):
    ws = wb.create_sheet("민감도")
    title(ws, "민감도 — 기준 3년차 연간 운영손익, 한 변수씩 ±20%",
          "적용 L 기준. 수수료율은 고정(별도 참고). 유료 전환 = 전체 병원 수는 그대로 두고 프리미엄 병원 수만 ±20%.")
    s = "기준"
    ws["A4"] = "기준 3년차 연간 운영손익"
    ws["B4"] = f"='{QS}'!$P${PNL[(s, 'op')]}"
    ws["B4"].number_format = "#,##0"
    ws["B4"].font = BOLD
    r = 6
    for j, h in enumerate(["변수", "−20% 결과", "+20% 결과", "변화 폭", "순위"], 1):
        ws.cell(row=r, column=j, value=h)
    style_header(ws, r, 5)
    first, last = r + 1, r + len(order)
    for key, name in order:
        r += 1
        SE[key] = r
        ws.cell(row=r, column=1, value=name)
        ws.cell(row=r, column=2, value=sens_formula(key, 0.8)).number_format = "#,##0"
        ws.cell(row=r, column=3, value=sens_formula(key, 1.2)).number_format = "#,##0"
        ws.cell(row=r, column=4, value=f"=ABS(C{r}-B{r})").number_format = "#,##0"
        ws.cell(row=r, column=5, value=f'=1+COUNTIF($D${first}:$D${last},">"&D{r})')
    r += 2
    ws.cell(row=r, column=1, value="스트레스: 진료 완료 50% 감소 (두 요금제 모두)").font = BOLD
    P = lambda k: f"'{QS}'!$P${PNL[(s, k)]}"
    SE["stress"] = r
    ws.cell(row=r, column=2, value=f"={P('op')}-0.5*({P('fee_b')}+{P('fee_p')}-{P('var_deal')})").number_format = "#,##0"
    r += 2
    ws.cell(row=r, column=1, value="민감도 1위 변수가 MVP에서 먼저 검증할 가설(Day15 19쪽). 순서는 생성 시 기준값으로 정렬, 순위 열은 수식.").font = NOTE
    ws.column_dimensions["A"].width = 44
    for c in "BCDE":
        ws.column_dimensions[c].width = 18


def build_market(wb):
    ws = wb.create_sheet("시장규모")
    title(ws, "시장규모 — 기존 TAM·SAM 승계와 이번 모델 연결",
          "진료비 시장과 플랫폼 매출은 단위가 다름. 시장 점유율 방식과 병원 수 방식은 교차 확인용이며 합산하지 않음.")
    for j, h in enumerate(["항목"] + YN + ["단위", "읽는 법"], 1):
        ws.cell(row=4, column=j, value=h)
    style_header(ws, 4, 6)
    s = "기준"
    q = lambda k, col: f"='{QS}'!{col}{PNL[(s, k)]}"
    rows = [
        ("TAM 환자", "='자료'!B7", "", "", "명", "제공문서"),
        ("TAM 진료비 추정", "='자료'!B9", "", "", "원/년", "제공문서"),
        ("SAM 환자", "='자료'!B5", "=B7*(1+'자료'!B12)", "=C7*(1+'자료'!B12)", "명/년", "연 12.8% 성장 참고 가정"),
        ("SAM 진료비", "='자료'!B6", "=B8*(1+'자료'!B12)", "=C8*(1+'자료'!B12)", "원/년", "병원 진료비, 플랫폼 매출 아님"),
        ("연말 병원 수 (기준 경로)", f"='가정'!E{REF['path_total']}", f"='가정'!I{REF['path_total']}", f"='가정'!M{REF['path_total']}", "곳", "연평균 아님"),
        ("상향식 진료 완료 (기준)", q("d", "N"), q("d", "O"), q("d", "P"), "건", "분기 평균 병원 기준"),
        ("상향식 진료 거래액 (기준)", q("gmv", "N"), q("gmv", "O"), q("gmv", "P"), "원", ""),
        ("상향식 플랫폼 매출 (기준)", q("rev", "N"), q("rev", "O"), q("rev", "P"), "원", "수수료 + 구독료 + 광고"),
        ("진료 완료 ÷ SAM 환자", "=B10/B7", "=C10/C7", "=D10/D7", "%", "단위가 달라 잠정 비율(교차 확인)"),
        ("거래액 ÷ SAM 진료비", "=B11/B8", "=C11/C8", "=D11/D8", "%", "기존 SOM 점유율 2% 가정과 비교"),
    ]
    for i, row in enumerate(rows, 5):
        for j, v in enumerate(row, 1):
            ws.cell(row=i, column=j, value=v)
        fmt = "0.00%" if row[4] == "%" else "#,##0"
        for col in "BCD":
            ws[f"{col}{i}"].number_format = fmt
    ws.column_dimensions["A"].width = 30
    for c in "BCD":
        ws.column_dimensions[c].width = 20
    ws.column_dimensions["F"].width = 40


def copy_sheet(src, dst):
    for row in src.iter_rows():
        for c in row:
            if type(c).__name__ == "MergedCell":
                continue
            if c.value is None and not c.has_style:
                continue
            d = dst.cell(row=c.row, column=c.column, value=c.value)
            if c.has_style:
                d.font, d.fill, d.border = copy(c.font), copy(c.fill), copy(c.border)
                d.alignment, d.number_format = copy(c.alignment), c.number_format
    for k, dim in src.column_dimensions.items():
        dst.column_dimensions[k].width = dim.width
    for rng in src.merged_cells.ranges:
        dst.merge_cells(str(rng))
    dst.freeze_panes = src.freeze_panes


def build_gaps(wb):
    ws = wb.create_sheet("부족데이터")
    title(ws, "부족데이터 — 가정으로 채운 값과 실측으로 바꿀 값",
          "이번 모델은 빈칸 대신 '새 가정'을 넣어 손익을 계산했다. 아래 순서대로 실측·팀 결정으로 교체.")
    for j, h in enumerate(["우선", "항목", "이번에 넣은 값 (기준)", "상태", "바꾸는 방법", "가정 시트"], 1):
        ws.cell(row=4, column=j, value=h)
    style_header(ws, 4, 6)
    rows = [
        (1, "팀 전체 월 인건비 L", "4명 × 주 4일 × 하루 4시간 = 월 345.1만 원 (2026 최저임금)", "팀 결정 반영", "실제 근무시간·급여 확정. 2027 최저임금이면 월 약 357.8만 원", f"C{L_ROWS[0]}:C{L_ROWS[-1]}"),
        (1, "건당 진료비", "73만 원 (BM 문서는 100만)", "문서 간 불일치", "진흥원 카드데이터 표·병원 정가로 1개 기준 확정", f"자료!B13 · 행 {ROW['deal_value']}"),
        (1, "문의→예약·예약→완료 전환율", "20% · 50%", "실측 없음", "MVP 챗봇·예약 로그로 측정", f"행 {ROW['conv_book']}~{ROW['conv_done']}"),
        (1, "병원당 월 진료 완료", "기본 0.5 · 프리미엄 4건", "팀 가정", "입점 병원 파일럿 실적", f"행 {ROW['deals_basic']}~{ROW['deals_prem']}"),
        (1, "3년차 병원 경로", "46 → 67곳, 프리미엄 6 → 10곳", "새 가정", "2년차 영업 실적으로 다시 잡기", f"행 {REF['path_total']}~{REF['path_prem']} J~M열"),
        (2, "광고 배너 수익", "월 15만 원, 1개월차부터", "팀 제공값", "광고주·계약 단가 확인, 의료광고 규제 확인", f"행 {ROW['ad_rev']}"),
        (2, "환자 마케팅비", "월 50만 원", "새 가정", "채널별 실험 예산과 신규 완료 고객 추적 → 실제 CAC", f"행 {ROW['mkt']}"),
        (2, "병원 온보딩 현금지출", "곳당 10만 원", "새 가정", "실제 영업 지출 기록", f"행 {ROW['onboard']}"),
        (2, "문의당 AI·번역비", "100원", "새 가정", "사용 모델 공식 단가 × 테스트 대화 토큰", f"행 {ROW['ai_cost']}"),
        (2, "결제·정산·CS비", "건당 4,000원", "팀 가정", "결제 흐름 확정 후 PG·정산 견적", f"행 {ROW['payment']}"),
        (3, "보증보험료", "월 10만 원 (기타 고정비 안)", "견적 필요", "서울보증 영업점 견적", f"행 {ROW['other_fixed']}"),
        (3, "초기 일회성 지출·정산 조건", "0원 · 1개월", "미확정", "구축·등록 비용, 병원 정산 계약", f"행 {ROW['initial_out']}~{ROW['settle_lag']}"),
        (3, "프리미엄 회원비 규제 처리", "요금안 v4 유지", "미확인", "유치업 등록·계약 적법성 공식 질의", "별도 검토 문서"),
    ]
    for i, row in enumerate(rows, 5):
        for j, v in enumerate(row, 1):
            ws.cell(row=i, column=j, value=v)
    for i, w in enumerate([6, 28, 40, 16, 52, 24], 1):
        ws.column_dimensions[CL(i)].width = w


def build_levers_sheet(wb, res):
    ws = wb.create_sheet("개선방안")
    title(ws, "개선방안 — 기준 시나리오에서 한 가지씩 바꿨을 때 (3년, Python 계산값)",
          "이 시트의 숫자는 build_profit_model.py가 계산한 값이다. '바꿀 칸'을 가정 시트에서 바꾸면 연간손익·인건비비교가 같은 값으로 다시 계산된다(verify_formulas.md에서 묶음 B 재현 확인).")
    hdr = ["방법", "구분", "무엇을 바꾸나", "실행 방법", "가정 시트에서 바꿀 칸"]
    for _, lab, _ in L_LEVELS:
        hdr += [f"[L {lab}] 첫 흑자 연도", f"[L {lab}] 3년 손익", f"[L {lab}] 개선 폭", f"[L {lab}] 필요자금"]
    for j, h in enumerate(hdr, 1):
        ws.cell(row=4, column=j, value=h)
    style_header(ws, 4, len(hdr))
    r = 4
    for x in res["combos"] + res["levers"] + res["ref_levers"]:
        r += 1
        for j, v in enumerate([x["name"], x["group"], x["change"], x["how"], x["cells"]], 1):
            ws.cell(row=r, column=j, value=v).alignment = Alignment(wrap_text=True, vertical="top")
        col = 6
        for y in x["by_L"]:
            for v in (y["first_year"] or "없음", y["op_total"], y["delta"], y["need"]):
                c = ws.cell(row=r, column=col, value=v)
                if not isinstance(v, str):
                    c.number_format = "#,##0"
                col += 1
        if x["group"] == "묶음":
            for j in range(1, len(hdr) + 1):
                ws.cell(row=r, column=j).fill = BLUE
    for i, w in enumerate([26, 10, 34, 46, 44] + [13] * 12, 1):
        ws.column_dimensions[CL(i)].width = w
    ws.freeze_panes = "B5"


def build_guide(wb):
    ws = wb.active
    ws.title = "안내"
    title(ws, "메디대구 수익 시뮬레이션 — 3년 (연 단위 · 요금안 v4)",
          "생성: simulation/build_profit_model.py · 기준 원본: source/실습양식 엑셀 · 결과 요약: simulation/pnl_sim.md")
    lines = [
        ("검증 질문", "현재 요금으로 거래를 만들었을 때 얼마가 남고, 몇 년차에 운영비를 감당하며, 그 전까지 얼마의 자금이 필요한가?"),
        ("이번 변경 (v3)", "기간 3년·1년 단위 · 팀 인건비 = 4명 × 주 4일 × 하루 4시간(월 345.1만 원) · 웹사이트 하단 광고 배너 월 15만 원. 나머지 가정은 v1과 같음"),
        ("셀 색", "노란 칸 = 입력 가정 · 나머지 숫자 칸은 모두 수식"),
        ("가정", "요금·거래·광고·전환·비용·인건비 L 3단계·병원 확보 경로(3년)"),
        ("연간손익", "보수·기준·낙관 1~3년차 결과 (먼저 볼 시트)"),
        ("분기계산", "병원 순차 입점을 반영한 3개월 단위 바탕 계산 (연간손익이 읽는 시트)"),
        ("현금흐름", "정산 지연 반영 누적 잔액, 최대 부족액, 필요 초기자금"),
        ("인건비비교", "시나리오 3 × L 3단계: 첫 흑자 연도, 3년 누적손익, 필요 초기자금"),
        ("단위경제", "거래 1건·병원 1곳·환자 1명: 공헌이익, CAC, LTV/CAC, 회수기간"),
        ("계단표", "3년차 마지막 분기 기준 거래량 배수별 월 손익, L 단계별 손익분기 거래 수"),
        ("민감도", "기준 3년차 연간 손익, 변수 하나씩 ±20%, 거래 50% 감소 스트레스"),
        ("개선방안", "흑자로 바꾸려면: 팀이 바꿀 수 있는 7가지·요금 참고 2가지·묶음 2가지의 효과와 바꿀 칸"),
        ("시장규모", "기존 TAM·SAM과 이번 모델의 거래·매출 연결 (교차 확인용)"),
        ("자료 · 경쟁비교", "실습양식 엑셀에서 그대로 복사 (케어랩스·So-Young 원문 값)"),
        ("부족데이터", "가정으로 채운 값과 실측으로 바꿀 순서"),
        ("주의", "운영손익은 관리용 지표 — 세금·감가상각·금융비용·부가세 제외. 숫자는 추정이며 실적이 아님."),
    ]
    for i, (a, b) in enumerate(lines, 4):
        ws.cell(row=i, column=1, value=a).font = BOLD
        ws.cell(row=i, column=2, value=b)
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 120


def build_workbook(sens_order, res=None):
    src = openpyxl.load_workbook(SRC)
    wb = openpyxl.Workbook()
    build_guide(wb)
    build_assumptions(wb)
    build_quarterly(wb)
    build_cashflow(wb)
    build_annual(wb)
    build_labor_compare(wb)
    build_unit(wb)
    build_steps(wb)
    build_sensitivity(wb, sens_order)
    if res:
        build_levers_sheet(wb, res)
    build_market(wb)
    for name in ("자료", "경쟁비교"):
        copy_sheet(src[name], wb.create_sheet(name))
    build_gaps(wb)
    # 보는 순서: 안내 → 가정 → 연간손익 → …
    order = ["안내", "가정", "연간손익", "인건비비교", "현금흐름", "분기계산", "단위경제", "계단표", "민감도", "개선방안",
             "시장규모", "자료", "경쟁비교", "부족데이터"]
    wb._sheets = [wb[n] for n in order if n in wb.sheetnames]
    OUT.parent.mkdir(exist_ok=True)
    wb.save(OUT)


# ───────────────────────── results.json ─────────────────────────
def build_results():
    runs = []
    for sc in SC:
        p = params(sc)
        for li, (L, _, _) in enumerate(L_LEVELS):
            qs = simulate(p, L)
            runs.append(dict(scenario=sc, L_index=li, quarters=qs, years=yearly(qs), summary=summarize(qs, p, L)))
    pb = params("기준")
    Lsel = L_LEVELS[L_SELECTED - 1][0]
    base = y3_op(pb, Lsel)
    sens = []
    for key, name in SENS:
        lo, hi = y3_op(pb, Lsel, {key: 0.8}), y3_op(pb, Lsel, {key: 1.2})
        sens.append(dict(key=key, name=name, minus=lo, plus=hi, range=abs(hi - lo)))
    sens.sort(key=lambda s: -s["range"])
    y3 = yearly(simulate(pb, Lsel))[2]
    var_deal3 = sum(q["var_deal"] for q in simulate(pb, Lsel)[8:])
    stress = y3["op"] - 0.5 * (y3["fee_basic"] + y3["fee_prem"] - var_deal3)
    # 손익분기 (Q12)
    q12 = simulate(pb, Lsel)[-1]
    D = q12["deals"] / 3
    var_prem = q12["prem_avg"] * pb["prem_addl"] * 3
    V = (q12["fee_basic"] + q12["fee_prem"] - q12["var_deal"]) / 3
    F0 = (q12["sub"] + q12["ad"] - var_prem - q12["fixed"] - q12["mkt"] - q12["onboard"]) / 3
    be = [dict(label=lab, L=L, need=max(0, (L - F0) / V) * D, have=D,
               hospitals=max(0, (L - F0) / V) * (q12["basic_avg"] + q12["prem_avg"])) for L, lab, _ in L_LEVELS]
    # 단위경제 (기준)
    c_deal = pb["inq_per_deal"] * pb["ai_cost"] + pb["support"] + pb["payment"]
    cb = pb["deal_value"] * pb["fee_basic"] - c_deal
    cp = pb["deal_value"] * pb["fee_prem"] - c_deal
    hb, hp = cb * pb["deals_basic"], cp * pb["deals_prem"] + pb["sub_fee"] - pb["prem_addl"]
    rb = next(r for r in runs if r["scenario"] == "기준" and r["L_index"] == L_SELECTED - 1)
    qs, ys = rb["quarters"], rb["years"]
    cacs = [pb["mkt"] * 12 / y["deals"] for y in ys]
    dl = sum(q["deals"] for q in qs)
    avg_c = sum(q["fee_basic"] + q["fee_prem"] - q["var_deal"] for q in qs) / dl
    ltv = avg_c * pb["repeat"]
    unit = dict(deal=pb["deal_value"], fee_b=pb["deal_value"] * pb["fee_basic"], fee_p=pb["deal_value"] * pb["fee_prem"],
                cost=c_deal, cb=cb, cp=cp, hb=hb, hp=hp, inq=pb["inq_per_deal"], cac1=cacs[0], cac2=cacs[1], cac3=cacs[2],
                ltv=ltv, ltvcac=[ltv / c for c in cacs], hcac=pb["onboard"], pay_b=pb["onboard"] / hb, pay_p=pb["onboard"] / hp,
                even_amt=pb["sub_fee"] / (pb["fee_basic"] - pb["fee_prem"]),
                even_n=pb["sub_fee"] / (pb["fee_basic"] - pb["fee_prem"]) / pb["deal_value"])
    w = lambda v: f"{v:,.0f}원"
    unit_rows = [
        ["건당 진료비 (객단가)", w(unit["deal"])],
        ["건당 수수료 — 기본 13% / 프리미엄 8%", f"{w(unit['fee_b'])} / {w(unit['fee_p'])}"],
        ["완료 1건당 문의 수 · 직접비", f"{unit['inq']:.0f}건 · {w(unit['cost'])}"],
        ["건당 공헌이익 — 기본 / 프리미엄", f"{w(cb)} / {w(cp)}"],
        ["병원 월 공헌이익 — 기본(0.5건) / 프리미엄(4건+구독)", f"{w(hb)} / {w(hp)}"],
        ["병원 CAC · 회수기간 (기본 / 프리미엄)", f"{w(pb['onboard'])} · {unit['pay_b']:.1f}개월 / {unit['pay_p']:.1f}개월"],
        ["환자 CAC — 1년차 / 2년차 / 3년차", " / ".join(w(c) for c in cacs)],
        ["환자 LTV (이용 1회) · LTV/CAC 1→3년차", f"{w(ltv)} · " + " / ".join(f"{x:.2f}" for x in unit["ltvcac"])],
        ["두 요금제 부담이 같은 월 거래", f"{w(unit['even_amt'])} ≈ {unit['even_n']:.2f}건"],
    ]
    concl = json.loads(CONCLUSIONS.read_text(encoding="utf-8")) if CONCLUSIONS.exists() else {}
    res = dict(
        version="v4 · 구독료 없음(기본 13% · 프리미엄 8% 진료비 수수료) · 3년·연 단위 · 인건비 4명×주 4일×4시간 · 광고 배너 월 15만 원",
        scenarios=SC, years=YN,
        L_levels=[dict(L=L, label=lab, desc=desc) for L, lab, desc in L_LEVELS],
        L_selected=L_SELECTED - 1,
        runs=runs,
        sensitivity=sens, sens_base=base, stress=stress,
        sensitivity_note=f"기준 3년차 연간 운영손익 {base:,.0f}원 (L {L_LEVELS[L_SELECTED-1][1]}). 거래 50% 감소 시 {stress:,.0f}원.",
        unit=unit_rows, unit_raw=unit, breakeven=be,
        breakeven_note="3년차 마지막 분기(Q12)의 평균 병원 수·구독·광고·고정비를 고정하고 진료 완료 건수만 늘릴 때. 처리 능력 확대 비용은 미반영.",
        conclusions=concl.get("conclusions", []), cautions=concl.get("cautions", []), lever_summary=concl.get("lever_summary", []),
        levers=[lever_result(lv) for lv in LEVERS], ref_levers=[lever_result(lv) for lv in REF_LEVERS],
        combos=[lever_result(lv) for lv in COMBOS],
    )
    RESULTS.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


def build_snapshot():
    """서버 없이 더블클릭으로 여는 대시보드 한 파일 (결과·진행 기록을 HTML 안에 넣음)"""
    html = (BASE / "dashboard" / "index.html").read_text(encoding="utf-8")
    prog_path = BASE / "output" / "progress.json"
    data = {"results": json.loads(RESULTS.read_text(encoding="utf-8")),
            "progress": json.loads(prog_path.read_text(encoding="utf-8")) if prog_path.exists() else None}
    inject = "<script>window.__SNAPSHOT__ = " + json.dumps(data, ensure_ascii=False) + ";</script>\n"
    out = BASE / "output" / "수익시뮬레이션_대시보드.html"
    marker = "<script>\nconst man"
    assert marker in html, "dashboard/index.html 구조가 바뀜 — marker 확인"
    out.write_text(html.replace(marker, inject + marker, 1), encoding="utf-8")
    return out


if __name__ == "__main__":
    res = build_results()
    build_workbook([(s["key"], s["name"]) for s in res["sensitivity"]], res)
    print("saved", OUT, RESULTS, build_snapshot())
