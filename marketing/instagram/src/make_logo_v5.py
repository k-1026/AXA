"""메디대구 로고 v5 시안 — 글자 M에 기대지 않는 심볼 (2026-11-20).

색은 그대로: 파랑 #1f6feb 바탕 · 흰색 · 연하늘 #e3edfd 포인트. 아래 글자는 'MediDaegu' 한 줄.
- G 산 고리: 봉우리들이 둥글게 둘러싼 고리(분지) 한가운데 진료 십자 → "산에 둘러싸인 대구 안의 병원"
- H 상담 말풍선: 말풍선 안에 대구 산 능선과 그 위의 십자 → "내 언어로 대구 병원 상담" (서비스 핵심: 상담 예약·챗봇)
- I 사과 십자: 사과 모양 안을 십자로 뚫음 + 잎 → "대구 사과 + 진료" — 추천·적용
(대구가 분지·사과로 알려졌다는 점은 디자인 근거라 출처 확인 필요)

    python -I -X utf8 make_logo_v5.py   → src/logo_G.html, logo_H.html, logo_I.html, logo_sheet_v5.html
"""
import math
from pathlib import Path

HERE = Path(__file__).parent
BLUE, SKY, NAVY = "#1f6feb", "#e3edfd", "#172b4d"


def page(svg):
    return f"""<!doctype html><meta charset="utf-8"><style>*{{margin:0}}html,body{{width:1080px;height:1080px;overflow:hidden;background:{BLUE}}}</style>
<svg viewBox="0 0 1080 1080" width="1080" height="1080" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, sans-serif">{svg}</svg>"""


WORD = """<text x="540" y="880" text-anchor="middle" font-size="96" font-weight="800" fill="#fff" letter-spacing="2">Medi<tspan fill="%s">Daegu</tspan></text>""" % SKY


def cross(cx, cy, size, thick, color):
    h = size / 2
    t = thick / 2
    r = thick * 0.25
    return (f'<rect x="{cx - t}" y="{cy - h}" width="{thick}" height="{size}" rx="{r}" fill="{color}"/>'
            f'<rect x="{cx - h}" y="{cy - t}" width="{size}" height="{thick}" rx="{r}" fill="{color}"/>')


# G: 봉우리 고리 — 원 둘레를 따라 바깥으로 솟은 산 9개
def ring(cx, cy, r_in, r_out, n):
    pts = []
    for i in range(n * 2):
        a = -math.pi / 2 + i * math.pi / n
        r = r_out if i % 2 == 0 else r_in
        pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
    return " ".join(pts)


LOGO_G = page(f"""
<polygon points="{ring(540, 430, 230, 330, 9)}" fill="#fff" stroke="#fff" stroke-width="18" stroke-linejoin="round"/>
<circle cx="540" cy="430" r="200" fill="{BLUE}"/>
{cross(540, 430, 210, 70, SKY)}
{WORD}""")

# H: 말풍선 + 산 능선 + 십자
LOGO_H = page(f"""
<path d="M540 140c-200 0-340 120-340 280 0 110 66 200 170 248l-30 102 120-80c26 6 52 10 80 10 200 0 340-120 340-280S740 140 540 140z" fill="#fff"/>
<polyline points="300,560 400,470 470,520 560,430 660,510 780,560" fill="none" stroke="{SKY}" stroke-width="34" stroke-linejoin="round" stroke-linecap="round"/>
{cross(540, 340, 180, 58, BLUE)}
{WORD}""")

# I: 사과 + 십자 구멍 + 잎
LOGO_I = page(f"""
<path d="M540 300c-40-40-150-50-200 30-50 85-20 220 50 300 45 50 90 60 150 30 60 30 105 20 150-30 70-80 100-215 50-300-50-80-160-70-200-30z" fill="#fff"/>
<path d="M540 300c0-50 12-90 36-120" stroke="#fff" stroke-width="26" fill="none" stroke-linecap="round"/>
<path d="M580 200c40-55 110-60 150-30-25 55-100 75-150 30z" fill="{SKY}"/>
{cross(540, 480, 200, 66, BLUE)}
{WORD}""")

SHEET = f"""<!doctype html><meta charset="utf-8"><style>*{{margin:0;box-sizing:border-box}}
body{{width:1500px;background:#fff;font-family:"Segoe UI","Malgun Gothic",sans-serif;color:{NAVY};padding:40px}}
.row{{display:flex;gap:40px}}.c{{flex:1;text-align:center}}
.big{{width:400px;height:400px;border-radius:50%;overflow:hidden;margin:0 auto}}
.big img,.sm img{{width:100%;height:100%}}
.sm{{width:110px;height:110px;border-radius:50%;overflow:hidden;margin:16px auto 0}}
h2{{font-size:30px;margin-top:20px}}p{{font-size:20px;color:#5b6673;margin-top:8px;line-height:1.4}}
</style><div class="row">
<div class="c"><div class="big"><img src="../logo_G.png"></div><div class="sm"><img src="../logo_G.png"></div><h2>G · 산 고리</h2><p>봉우리가 둘러싼 분지<br>한가운데 진료 십자</p></div>
<div class="c"><div class="big"><img src="../logo_H.png"></div><div class="sm"><img src="../logo_H.png"></div><h2>H · 상담 말풍선</h2><p>말풍선 = 내 언어로 상담<br>대구 산 능선 위 십자</p></div>
<div class="c"><div class="big"><img src="../logo_I.png"></div><div class="sm"><img src="../logo_I.png"></div><h2>I · 사과 십자 (추천)</h2><p>대구 사과 안을<br>십자로 뚫음</p></div>
</div>"""

for name, html in [("logo_G", LOGO_G), ("logo_H", LOGO_H), ("logo_I", LOGO_I), ("logo_sheet_v5", SHEET)]:
    (HERE / f"{name}.html").write_text(html, encoding="utf-8")
print("ok")
