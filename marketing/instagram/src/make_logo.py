"""메디대구 로고 v3 시안 — 'M'(Medi) + 대구 특징 (2026-11-20).

색은 그대로: 파랑 #1f6feb 바탕 · 흰 글자 · 연하늘 #e3edfd 포인트
대구 특징
- A 사과: 브랜드 점을 '대구 사과'로 (잎 + 꼭지). 대구는 사과로 알려진 도시라 한눈에 지역이 보이게
- B 위치 핀: M 오른쪽 위 끝에 핀 → "대구에서 병원 찾기" (지도 기능) — 2026-11-20 적용안
- C 약령시: M 아래 'DAEGU' 띠 + 약초 잎 → 대구약령시(오래된 한약재 시장)에서 '메디'와 '대구'를 같이

    python -I -X utf8 make_logo.py   → src/logo_A.html, logo_B.html, logo_C.html, logo_sheet.html
"""
from pathlib import Path

HERE = Path(__file__).parent
BLUE, SKY, NAVY = "#1f6feb", "#e3edfd", "#172b4d"

HEAD = """<!doctype html><meta charset="utf-8"><style>*{margin:0}html,body{width:1080px;height:1080px;overflow:hidden}
body{background:%s;position:relative;font-family:"Segoe UI",sans-serif}</style>""" % BLUE

# A: M + 사과 점 + DAEGU
APPLE = """<svg viewBox="0 0 120 130" width="{s}" height="{s}" style="position:absolute;left:{x}px;top:{y}px">
<path d="M60 34c-8-8-30-10-40 6-10 17-4 44 10 60 9 10 18 12 30 6 12 6 21 4 30-6 14-16 20-43 10-60-10-16-32-14-40-6z" fill="{c}"/>
<path d="M60 36c0-12 3-20 9-28" stroke="{c}" stroke-width="7" fill="none" stroke-linecap="round"/>
<path d="M70 14c10-12 26-12 34-6-6 12-22 16-34 6z" fill="{c}"/>
</svg>"""

LOGO_A = HEAD + f"""
<div style="position:absolute;left:0;right:0;top:170px;text-align:center;color:#fff;font-weight:900;font-size:520px;line-height:1;letter-spacing:-.04em">M</div>
{APPLE.format(s=200, x=705, y=150, c=SKY)}
<div style="position:absolute;left:0;right:0;top:735px;text-align:center;color:#fff;font-weight:800;font-size:92px;letter-spacing:.32em;padding-left:.32em">DAEGU</div>
"""

# B: M 골짜기에 위치 핀 + MEDI·DAEGU
PIN = """<svg viewBox="0 0 100 130" width="{w}" height="{h}" style="position:absolute;left:{x}px;top:{y}px">
<path d="M50 4C25 4 8 22 8 46c0 30 42 78 42 78s42-48 42-78C92 22 75 4 50 4z" fill="{c}"/>
<circle cx="50" cy="46" r="16" fill="{b}"/></svg>"""
LOGO_B = HEAD + f"""
<div style="position:absolute;left:0;right:0;top:160px;text-align:center;color:#fff;font-weight:900;font-size:520px;line-height:1;letter-spacing:-.04em">M</div>
{PIN.format(w=165, h=215, x=718, y=88, c=SKY, b=BLUE)}
<div style="position:absolute;left:0;right:0;top:740px;text-align:center;color:#fff;font-weight:800;font-size:76px;letter-spacing:.18em;padding-left:.18em">MEDI<span style="color:{SKY}">·</span>DAEGU</div>
"""

# C: M + 약초 잎 + 아래 연하늘 DAEGU 띠
LEAF = """<svg viewBox="0 0 120 120" width="{s}" height="{s}" style="position:absolute;left:{x}px;top:{y}px">
<path d="M14 106C14 50 50 14 106 14c0 56-36 92-92 92z" fill="{c}"/>
<path d="M22 98L92 28" stroke="{b}" stroke-width="7" stroke-linecap="round"/></svg>"""
LOGO_C = HEAD + f"""
<div style="position:absolute;left:0;right:0;top:150px;text-align:center;color:#fff;font-weight:900;font-size:500px;line-height:1;letter-spacing:-.04em">M</div>
{LEAF.format(s=150, x=770, y=150, c=SKY, b=BLUE)}
<div style="position:absolute;left:220px;right:220px;top:700px;height:130px;border-radius:65px;background:{SKY};color:{NAVY};display:grid;place-items:center;font-weight:900;font-size:84px;letter-spacing:.24em;padding-left:.24em">DAEGU</div>
"""

SHEET = f"""<!doctype html><meta charset="utf-8"><style>*{{margin:0;box-sizing:border-box}}
body{{width:1500px;background:#fff;font-family:"Segoe UI","Malgun Gothic",sans-serif;color:{NAVY};padding:40px}}
.row{{display:flex;gap:40px}}.c{{flex:1;text-align:center}}
.big{{width:400px;height:400px;border-radius:50%;overflow:hidden;margin:0 auto}}
.big img,.sm img{{width:100%;height:100%}}
.sm{{width:110px;height:110px;border-radius:50%;overflow:hidden;margin:16px auto 0}}
h2{{font-size:30px;margin-top:20px}}p{{font-size:20px;color:#5b6673;margin-top:8px;line-height:1.4}}
</style><div class="row">
<div class="c"><div class="big"><img src="../logo_A.png"></div><div class="sm"><img src="../logo_A.png"></div><h2>A · 사과</h2><p>브랜드 점을 '대구 사과'로<br>M + DAEGU</p></div>
<div class="c"><div class="big"><img src="../logo_B.png"></div><div class="sm"><img src="../logo_B.png"></div><h2>B · 위치 핀 (적용)</h2><p>M 오른쪽 위 끝에 핀<br>"대구에서 병원 찾기"</p></div>
<div class="c"><div class="big"><img src="../logo_C.png"></div><div class="sm"><img src="../logo_C.png"></div><h2>C · 약령시 잎</h2><p>약초 잎 + DAEGU 띠<br>대구약령시에서 '메디'+'대구'</p></div>
</div>"""

for name, html in [("logo_A", LOGO_A), ("logo_B", LOGO_B), ("logo_C", LOGO_C), ("logo_sheet", SHEET)]:
    (HERE / f"{name}.html").write_text(html, encoding="utf-8")
print("ok")
