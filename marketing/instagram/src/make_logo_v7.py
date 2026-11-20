"""메디대구 로고 v7 시안 — MD를 다시 조합해 '청진기'를 살짝 떠올리게 (2026-11-20).

v6(MD 모노그램, 흰 배경, 십자 없음)의 선 굵기·색·글자(MEDI / DAEGU)는 그대로 두고 M과 D만 바꿔요.
청진기 부품 ↔ 글자
- 귀꽂이 2개 = M 위쪽 두 끝의 작은 점
- Y자 관 = M 가운데 V
- 고무관 = D의 둥근 선
- 청진판(가슴에 대는 둥근 판) = 작은 고리

시안
- S1 귀꽂이만: M 위 두 끝에 점 → 가장 은근함
- S2 귀꽂이 + D 안 청진판: 점 + D 빈 공간 정가운데에 작은 고리
- S3 M 안 청진기: 점 + M의 V 꼭짓점에서 관이 내려와 다리 사이 고리(청진판)로 끝남 → M 자체가 청진기, D는 그대로

    python -I -X utf8 make_logo_v7.py
"""

from pathlib import Path

HERE = Path(__file__).parent
BLUE, SKY, WHITE = "#1f6feb", "#e3edfd", "#ffffff"
CX = 975
V_Y = 108


def mono(color, sw, variant):
    ear = round(sw * 0.62)  # 귀꽂이 점 반지름 (선보다 조금 굵게)
    parts = [f"""<g fill="none" stroke="{color}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="butt">
<path d="M24 228 V24 L96 {V_Y} L168 24"/>
<path d="M168 24 H190 A102 102 0 0 1 190 228 H168 Z"/>
</g>""",
             f'<g fill="{color}"><circle cx="24" cy="18" r="{ear}"/><circle cx="168" cy="18" r="{ear}"/></g>']
    ring_w = round(sw * 0.7)
    if variant == "S2":
        parts.append(f'<circle cx="230" cy="126" r="26" fill="none" stroke="{color}" stroke-width="{ring_w}"/>')
    if variant == "S3":
        # M 자체를 청진기로: 귀꽂이(점) → V(Y자 관) → V 꼭짓점에서 내려오는 관 → 다리 사이 청진판(고리)
        r = 22
        parts.append(f'<path d="M96 {V_Y} V{196 - r}" fill="none" stroke="{color}" stroke-width="{ring_w}" stroke-linecap="butt"/>')
        parts.append(f'<circle cx="96" cy="196" r="{r}" fill="none" stroke="{color}" stroke-width="{ring_w}"/>')
    return "\n".join(parts)


def lockup(variant, bg=WHITE, fg=BLUE, sub=BLUE):
    return f"""<!doctype html><meta charset="utf-8"><style>*{{margin:0}}html,body{{width:1600px;height:800px;overflow:hidden;background:{bg}}}</style>
<svg viewBox="0 0 1600 800" width="1600" height="800" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, sans-serif">
<g transform="translate(330 260) scale(1.15)">{mono(fg, 24, variant)}</g>
<text x="{CX + 11}" y="440" text-anchor="middle" font-size="150" font-weight="600" fill="{fg}" letter-spacing="22">MEDI</text>
<text x="{CX + 15}" y="520" text-anchor="middle" font-size="46" font-weight="500" fill="{sub}" letter-spacing="30">DAEGU</text>
</svg>"""


def icon(variant, bg=WHITE, fg=BLUE):
    return f"""<!doctype html><meta charset="utf-8"><style>*{{margin:0}}html,body{{width:1080px;height:1080px;overflow:hidden;background:{bg}}}</style>
<svg viewBox="0 0 1080 1080" width="1080" height="1080" xmlns="http://www.w3.org/2000/svg">
<g transform="translate(240 290) scale(2.0)">{mono(fg, 30, variant)}</g>
</svg>"""


SHEET = """<!doctype html><meta charset="utf-8"><style>*{margin:0;box-sizing:border-box}
body{width:1500px;background:#fff;font-family:"Segoe UI","Malgun Gothic",sans-serif;color:#172b4d;padding:36px}
.row{display:flex;gap:30px}.c{flex:1;text-align:center}
.lk{width:100%;border:1px solid #e5e8ee;border-radius:12px}
.ic{width:120px;height:120px;border-radius:50%;border:1px solid #e5e8ee;margin:14px auto 0;overflow:hidden}.ic img{width:100%;height:100%}
h2{font-size:26px;margin-top:14px}p{font-size:18px;color:#5b6673;margin-top:6px;line-height:1.4}
</style><div class="row">
<div class="c"><img class="lk" src="../logo_v7_S1_lockup.png"><div class="ic"><img src="../logo_v7_S1_icon.png"></div><h2>S1 · 귀꽂이</h2><p>M 위 두 끝에 작은 점<br>가장 은근함</p></div>
<div class="c"><img class="lk" src="../logo_v7_S2_lockup.png"><div class="ic"><img src="../logo_v7_S2_icon.png"></div><h2>S2 · 귀꽂이 + 청진판</h2><p>점 + D 안 정가운데 고리</p></div>
<div class="c"><img class="lk" src="../logo_v7_S3_lockup.png"><div class="ic"><img src="../logo_v7_S3_icon.png"></div><h2>S3 · M 안 청진기</h2><p>V에서 관이 내려와 청진판으로<br>M 자체가 청진기, D는 그대로</p></div>
</div>"""

FILES = {}
for v in ("S1", "S2", "S3"):
    FILES[f"logo_v7_{v}_lockup"] = lockup(v)
    FILES[f"logo_v7_{v}_icon"] = icon(v)
FILES["logo_sheet_v7"] = SHEET

if __name__ == "__main__":
    for name, html in FILES.items():
        (HERE / f"{name}.html").write_text(html, encoding="utf-8")
    print("ok")
