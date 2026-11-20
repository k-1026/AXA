"""메디대구 로고 v8 (확정, 2026-11-20) — 팀이 고른 시안을 벡터로 다시 그림.

MD 모노그램에서 M의 오른쪽 기둥(= D의 기둥)이 아래로 내려와 **작은 고리(청진판)**로 끝나고,
D의 둥근 선이 그 고리에 이어짐 → M·D 글자는 그대로 읽히면서 청진기(관 + 청진판)가 살짝 보임.
선 굵기·색·글자(MEDI / 가운데 맞춘 DAEGU)는 v6 그대로.

만드는 것 (흰 배경이 기본, 파랑 배경은 보관용)
- logo_v8_lockup_white / _blue : 가로형 1600×800
- logo_v8_icon_white / _blue   : 아이콘 1080×1080 (프로필 사진 = 흰 배경, 선 굵기는 가로형과 같음)

    python -I -X utf8 make_logo_v8.py
"""
import math
from pathlib import Path

HERE = Path(__file__).parent
BLUE, SKY, WHITE = "#1f6feb", "#e3edfd", "#ffffff"
CX = 975
V_Y = 108
RING = (168, 228)  # 청진판 고리 중심 (D 기둥 아래 끝)


def mono(color, sw=24):
    # 청진판 고리: 선 굵기는 다른 선과 같게, 가운데 구멍이 보이게
    cx, cy = RING
    r = sw  # 고리 중심 반지름 (바깥 1.5배, 구멍 0.5배 굵기)
    # D의 위·아래 곧은 부분을 고리 크기만큼 늘려, D 아래 선이 수평으로 고리 오른쪽에 들어가게 함
    flat = cx + r * 1.5 + 6
    # 기둥 끝과 D 아래 선 끝은 고리 선 안쪽(중심 반지름)까지 → 고리가 덮어 이음새가 깔끔함
    return f"""<g fill="none" stroke="{color}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="butt">
<path d="M24 228 V24 L96 {V_Y} L168 24 V{cy - r}"/>
<path d="M168 24 H{flat:.1f} A102 102 0 0 1 {flat:.1f} 228 H{cx + r}"/>
<circle cx="{cx}" cy="{cy}" r="{r}"/>
</g>"""


def lockup(bg, fg, sub):
    return f"""<!doctype html><meta charset="utf-8"><style>*{{margin:0}}html,body{{width:1600px;height:800px;overflow:hidden;background:{bg}}}</style>
<svg viewBox="0 0 1600 800" width="1600" height="800" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, sans-serif">
<g transform="translate(330 260) scale(1.15)">{mono(fg)}</g>
<text x="{CX + 11}" y="440" text-anchor="middle" font-size="150" font-weight="600" fill="{fg}" letter-spacing="22">MEDI</text>
<text x="{CX + 15}" y="520" text-anchor="middle" font-size="46" font-weight="500" fill="{sub}" letter-spacing="30">DAEGU</text>
</svg>"""


def icon(bg, fg):
    return f"""<!doctype html><meta charset="utf-8"><style>*{{margin:0}}html,body{{width:1080px;height:1080px;overflow:hidden;background:{bg}}}</style>
<svg viewBox="0 0 1080 1080" width="1080" height="1080" xmlns="http://www.w3.org/2000/svg">
<g transform="translate(204 264) scale(2.0)">{mono(fg)}</g>
</svg>"""


FILES = {
    "logo_v8_lockup_white": lockup(WHITE, BLUE, BLUE),
    "logo_v8_lockup_blue": lockup(BLUE, WHITE, SKY),
    "logo_v8_icon_white": icon(WHITE, BLUE),
    "logo_v8_icon_blue": icon(BLUE, WHITE),
}
PROFILE_ICON = FILES["logo_v8_icon_white"]  # 프로필 사진: 흰 배경

if __name__ == "__main__":
    for name, html in FILES.items():
        (HERE / f"{name}.html").write_text(html, encoding="utf-8")
    print("ok")
