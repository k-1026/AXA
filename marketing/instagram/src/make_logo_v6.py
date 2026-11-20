"""메디대구 로고 v6 — MD 모노그램 (2026-11-20).

팀이 보여 준 참고 느낌: 굵기가 같은 선 하나로 그린 기하학적 이니셜 + 오른쪽에 큰 글자/작은 글자 두 줄.
이걸 MediDaegu의 약자 MD로: M의 오른쪽 기둥을 D의 기둥으로 같이 써서 두 글자를 한 모양으로 이음.

만드는 것 (파랑 배경 · 흰 배경) × (십자 있음 · 십자 없음)
- logo_v6_lockup_blue / _white        : 가로형, 십자 있음 (모노그램 + MEDI / DAEGU) 1600×800
- logo_v6_icon_blue / _white          : 아이콘, 십자 있음 1080×1080 — 프로필 사진용
- logo_v6_plain_lockup_blue / _white  : 가로형, 십자 없음
- logo_v6_plain_icon_blue / _white    : 아이콘, 십자 없음

    python -I -X utf8 make_logo_v6.py
"""
from pathlib import Path

HERE = Path(__file__).parent
BLUE, SKY, NAVY, WHITE = "#1f6feb", "#e3edfd", "#172b4d", "#ffffff"
CX = 975  # 가로형 글자 두 줄의 가운데
# M 가운데 V의 꼭짓점 높이: 132 → 108로 올려 V 사이 빈 공간을 줄임 (2026-11-20 팀 의견)
V_Y = 108
# D 안쪽 빈 공간의 정가운데: 기둥 x=168, 둥근 부분 원 중심 (190,126)·반지름 102 → 안쪽 가로 168~292의 가운데 230, 세로 24~228의 가운데 126
CROSS_X, CROSS_Y, ARM = 230, 126, 30


# 모노그램 (viewBox 0 0 300 240): 같은 굵기 선
def mono(color, sw=24, accent=None, cross=True):
    # M과 D가 오른쪽 기둥을 같이 씀. D는 닫힌 모양이라 아래 모서리가 깔끔하게 맞물림
    # 메디컬 느낌은 과하지 않게: D 안쪽 빈 공간 정가운데에 작은 각진 진료 십자 하나 (선 굵기는 조금 얇게)
    accent = accent or color
    cw = round(sw * 0.6)
    plus = f"""
<g fill="{accent}">
<rect x="{CROSS_X - cw / 2}" y="{CROSS_Y - ARM}" width="{cw}" height="{ARM * 2}"/>
<rect x="{CROSS_X - ARM}" y="{CROSS_Y - cw / 2}" width="{ARM * 2}" height="{cw}"/>
</g>""" if cross else ""
    return f"""<g fill="none" stroke="{color}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="butt">
<path d="M24 228 V24 L96 {V_Y} L168 24"/>
<path d="M168 24 H190 A102 102 0 0 1 190 228 H168 Z"/>
</g>{plus}"""


def lockup(bg, fg, sub, accent, cross=True):
    return f"""<!doctype html><meta charset="utf-8"><style>*{{margin:0}}html,body{{width:1600px;height:800px;overflow:hidden;background:{bg}}}</style>
<svg viewBox="0 0 1600 800" width="1600" height="800" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, sans-serif">
<g transform="translate(330 260) scale(1.15)">{mono(fg, accent=accent, cross=cross)}</g>
<!-- MEDI와 DAEGU를 같은 가운데 선에 맞춤 (자간이 마지막 글자 뒤에도 붙어서 그만큼 오른쪽으로 보정) -->
<text x="{CX + 11}" y="440" text-anchor="middle" font-size="150" font-weight="600" fill="{fg}" letter-spacing="22">MEDI</text>
<text x="{CX + 15}" y="520" text-anchor="middle" font-size="46" font-weight="500" fill="{sub}" letter-spacing="30">DAEGU</text>
</svg>"""


def icon(bg, fg, accent, cross=True):
    return f"""<!doctype html><meta charset="utf-8"><style>*{{margin:0}}html,body{{width:1080px;height:1080px;overflow:hidden;background:{bg}}}</style>
<svg viewBox="0 0 1080 1080" width="1080" height="1080" xmlns="http://www.w3.org/2000/svg">
<g transform="translate(255 300) scale(2.0)">{mono(fg, 30, accent, cross)}</g>
</svg>"""


FILES = {
    "logo_v6_lockup_blue": lockup(BLUE, WHITE, SKY, SKY),
    "logo_v6_lockup_white": lockup(WHITE, BLUE, BLUE, BLUE),
    "logo_v6_icon_blue": icon(BLUE, WHITE, SKY),
    "logo_v6_icon_white": icon(WHITE, BLUE, BLUE),
    "logo_v6_plain_lockup_blue": lockup(BLUE, WHITE, SKY, SKY, cross=False),
    "logo_v6_plain_lockup_white": lockup(WHITE, BLUE, BLUE, BLUE, cross=False),
    "logo_v6_plain_icon_blue": icon(BLUE, WHITE, SKY, cross=False),
    "logo_v6_plain_icon_white": icon(WHITE, BLUE, BLUE, cross=False),
}
ICON_BLUE = FILES["logo_v6_icon_blue"]
PROFILE_ICON = FILES["logo_v6_plain_icon_white"]  # 프로필 사진: 흰 배경 · 십자 없음 (2026-11-20 팀 결정)

if __name__ == "__main__":
    for name, html in FILES.items():
        (HERE / f"{name}.html").write_text(html, encoding="utf-8")
    print("ok")
