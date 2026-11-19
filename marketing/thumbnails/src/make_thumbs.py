"""메디대구 썸네일 v2 — 심플 + 기억에 남는 형태 (2026-11-19).

규칙 (모든 썸네일 공통)
- 바탕: 메디대구 파랑 #1f6feb 한 색
- 큰 글자 2줄(흰색)만. 설명 문장·단계 카드 없음
- 시그니처: 오른쪽 아래에 화면 밖으로 잘리는 아주 큰 연하늘 숫자/기호 (3 · ? 등) + 오른쪽 위 흰 점(브랜드 점)
- 아래 왼쪽에 작은 `MediDaegu` 글자, 강조 태그 1개(연하늘 #e3edfd 바탕, 남색 #172b4d 글자)

    python -I -X utf8 make_thumbs.py   → src/v2_*.html 생성
그다음 Chrome 헤드리스로 찍기 (README 참고).
"""
from pathlib import Path

HERE = Path(__file__).parent
FONT = {
    "en": '"Segoe UI","Malgun Gothic",sans-serif',
    "ja": '"Yu Gothic UI","Meiryo",sans-serif',
    "zh-TW": '"Microsoft JhengHei",sans-serif',
    "vi": '"Segoe UI",sans-serif',
}

# 이름: (파일, 언어, 너비, 높이, 제목 2줄, 태그, 큰 기호, 제목 크기)
THUMBS = [
    ("tiktok1_예약3단계", "zh-TW", 1080, 1920, "不會韓文<br>也能預約", "3 步驟・大邱看診", "3", 150),
    ("reels_en", "en", 1080, 1920, "No Korean?<br>Still book.", "3 steps · Daegu clinics", "3", 132),
    ("reels_ja", "ja", 1080, 1920, "韓国語なしで<br>予約OK", "3ステップ・大邱クリニック", "3", 132),
    ("reels_vi", "vi", 1080, 1920, "Không cần<br>tiếng Hàn", "3 bước · Phòng khám Daegu", "3", 132),
    ("tiktok2_진료시간QA", "zh-TW", 1080, 1920, "晚上<br>開到幾點？", "大邱診所・每日門診時間", "?", 150),
    ("insta1_가격읽는법_표지", "zh-TW", 1080, 1350, "價格<br>先看 3 處", "預約前存起來", "3", 150),
    ("dcard1_예약전체가이드_표지", "zh-TW", 1200, 630, "大邱看診<br>預約全攻略", "非業配・不推薦特定診所", "3", 96),
]


def html(lang, w, h, title, tag, mark, size):
    tall = h > w
    # 세로(9:16)는 틱톡·릴스 버튼이 가리는 아래쪽·오른쪽을 피해 위·가운데에 글자
    top = int(h * (0.26 if tall else 0.22))
    mark_size = int(h * (0.62 if tall else 1.15))
    pad = int(w * 0.083)
    tag_size = int(size * 0.34)
    return f"""<!doctype html><meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0}}
html,body{{width:{w}px;height:{h}px;overflow:hidden}}
body{{background:#1f6feb;color:#fff;font-family:{FONT[lang]};position:relative}}
.mark{{position:absolute;right:{-int(w*0.06)}px;bottom:{-int(mark_size*0.22)}px;font-family:"Segoe UI",sans-serif;font-weight:900;font-size:{mark_size}px;line-height:1;color:#e3edfd;opacity:.22}}
.dot{{position:absolute;top:{pad}px;right:{pad}px;width:{int(w*0.05)}px;height:{int(w*0.05)}px;border-radius:50%;background:#fff}}
h1{{position:absolute;top:{top}px;left:{pad}px;right:{pad}px;font-size:{size}px;line-height:1.18;font-weight:900;letter-spacing:-.01em}}
.tag{{position:absolute;left:{pad}px;top:{top + int(size*2.55)}px;background:#e3edfd;color:#172b4d;font-weight:700;font-size:{tag_size}px;padding:{int(tag_size*.35)}px {int(tag_size*.8)}px;border-radius:999px}}
.brand{{position:absolute;left:{pad}px;{'top:' + str(pad) + 'px' if tall else 'bottom:' + str(int(pad*0.8)) + 'px'};font-family:"Segoe UI",sans-serif;font-weight:700;font-size:{int(w*0.032)}px;letter-spacing:.02em}}
</style>
<div class="mark">{mark}</div>
<div class="dot"></div>
<div class="brand">MediDaegu</div>
<h1>{title}</h1>
<span class="tag">{tag}</span>
"""


for name, lang, w, h, title, tag, mark, size in THUMBS:
    (HERE / f"v2_{name}.html").write_text(html(lang, w, h, title, tag, mark, size), encoding="utf-8")
print("\n".join(f"{n} {w},{h}" for n, _, w, h, *_ in THUMBS))
