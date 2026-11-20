"""메디대구 로고 v4 시안 — '메디컬'과 '대구'가 더 잘 보이게, 다른 브랜드와 다르게 (2026-11-20).

색은 그대로: 파랑 #1f6feb 바탕 · 흰색 · 연하늘 #e3edfd 포인트
공통 아이디어: 대구는 산으로 둘러싸인 분지 도시 (디자인 근거, 출처 확인 필요)
- D 분지 M: M을 두 봉우리 산으로 그리고, 봉우리 사이(분지)에 진료 십자 → "산에 둘러싸인 대구 안의 병원"
- E 십자 핀: 흰 M 가운데에 핀, 핀 머리가 진료 십자 → "대구에서 찾는 병원"
- F 맥박 능선: 심전도 선이 산 능선이 되고 끝이 위치 핀 → "진료(맥박) + 대구 산 + 위치"

    python -I -X utf8 make_logo_v4.py   → src/logo_D.html, logo_E.html, logo_F.html, logo_sheet_v4.html
"""
from pathlib import Path

HERE = Path(__file__).parent
BLUE, SKY, NAVY = "#1f6feb", "#e3edfd", "#172b4d"


def page(svg):
    return f"""<!doctype html><meta charset="utf-8"><style>*{{margin:0}}html,body{{width:1080px;height:1080px;overflow:hidden;background:{BLUE}}}</style>
<svg viewBox="0 0 1080 1080" width="1080" height="1080" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, sans-serif">{svg}</svg>"""


WORD = f"""<text x="540" y="850" text-anchor="middle" font-size="88" font-weight="800" letter-spacing="10">
<tspan fill="#fff">MEDI</tspan><tspan fill="{SKY}">DAEGU</tspan></text>"""

# D: 두 봉우리 산 모양 M + 분지 안 십자
LOGO_D = page(f"""
<path d="M170 720 L370 300 Q405 240 440 300 L540 520 L640 300 Q675 240 710 300 L910 720 Z" fill="#fff"/>
<g fill="{SKY}"><rect x="524" y="340" width="32" height="104" rx="8"/><rect x="488" y="376" width="104" height="32" rx="8"/></g>
{WORD}""")

# E: 흰 M + 가운데 핀(머리에 십자)
LOGO_E = page(f"""
<text x="540" y="690" text-anchor="middle" font-size="560" font-weight="900" fill="#fff" letter-spacing="-20">M</text>
<path d="M540 250c-62 0-108 46-108 106 0 78 108 190 108 190s108-112 108-190c0-60-46-106-108-106z" fill="{SKY}"/>
<g fill="{BLUE}"><rect x="524" y="300" width="32" height="104" rx="8"/><rect x="488" y="336" width="104" height="32" rx="8"/></g>
{WORD}""")

# F: 심전도 → 산 능선 → 끝에 위치 핀
LOGO_F = page(f"""
<polyline points="150,600 330,600 380,520 450,330 520,560 580,420 640,600 700,600"
 fill="none" stroke="#fff" stroke-width="44" stroke-linejoin="round" stroke-linecap="round"/>
<path d="M820 400c-50 0-86 37-86 85 0 62 86 150 86 150s86-88 86-150c0-48-36-85-86-85z" fill="{SKY}"/>
<circle cx="820" cy="485" r="30" fill="{BLUE}"/>
{WORD}""")

SHEET = f"""<!doctype html><meta charset="utf-8"><style>*{{margin:0;box-sizing:border-box}}
body{{width:1500px;background:#fff;font-family:"Segoe UI","Malgun Gothic",sans-serif;color:{NAVY};padding:40px}}
.row{{display:flex;gap:40px}}.c{{flex:1;text-align:center}}
.big{{width:400px;height:400px;border-radius:50%;overflow:hidden;margin:0 auto}}
.big img,.sm img{{width:100%;height:100%}}
.sm{{width:110px;height:110px;border-radius:50%;overflow:hidden;margin:16px auto 0}}
h2{{font-size:30px;margin-top:20px}}p{{font-size:20px;color:#5b6673;margin-top:8px;line-height:1.4}}
</style><div class="row">
<div class="c"><div class="big"><img src="../logo_D.png"></div><div class="sm"><img src="../logo_D.png"></div><h2>D · 분지 M (추천)</h2><p>M = 대구를 둘러싼 두 봉우리<br>분지 안에 진료 십자</p></div>
<div class="c"><div class="big"><img src="../logo_E.png"></div><div class="sm"><img src="../logo_E.png"></div><h2>E · 십자 핀</h2><p>M 가운데 핀<br>핀 머리가 진료 십자</p></div>
<div class="c"><div class="big"><img src="../logo_F.png"></div><div class="sm"><img src="../logo_F.png"></div><h2>F · 맥박 능선</h2><p>심전도 선이 산 능선으로<br>끝에 위치 핀</p></div>
</div>"""

for name, html in [("logo_D", LOGO_D), ("logo_E", LOGO_E), ("logo_F", LOGO_F), ("logo_sheet_v4", SHEET)]:
    (HERE / f"{name}.html").write_text(html, encoding="utf-8")
print("ok")
