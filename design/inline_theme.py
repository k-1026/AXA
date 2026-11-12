"""design/theme.css를 문서 HTML 안에 직접 넣는다.

왜: HTML을 파일 미리보기(data: 주소)나 첨부로 열면 ../design/theme.css 같은 상대 경로를 못 찾아
스타일이 빠지고 SVG 상자가 검게 나온다. 그래서 각 HTML에 테마를 통째로 넣어 혼자서도 보이게 한다.

쓰는 법 (저장소 맨 위에서):  python design/inline_theme.py
theme.css를 고친 뒤 다시 돌리면 다섯 장이 모두 갱신된다.
"""
import io
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEME = (ROOT / "design" / "theme.css").read_text(encoding="utf-8")
PAGES = [
    "painpoint/journey_map.html",
    "painpoint/journey_3actors.html",
    "painpoint/priority.html",
    "bm/bm_canvas.html",
    "spec/userflow.html",
]
BLOCK = "<!-- theme:begin (design/theme.css, design/inline_theme.py로 갱신) -->\n<style>\n" + THEME.strip() + "\n</style>\n<!-- theme:end -->"
LINK = re.compile(r'<link rel="stylesheet" href="\.\./design/theme\.css">')
OLD = re.compile(r"<!-- theme:begin.*?<!-- theme:end -->", re.S)

for rel in PAGES:
    path = ROOT / rel
    html = path.read_text(encoding="utf-8")
    if OLD.search(html):
        html = OLD.sub(lambda _: BLOCK, html)
    elif LINK.search(html):
        html = LINK.sub(lambda _: BLOCK, html)
    else:
        raise SystemExit(f"{rel}: 테마 자리를 못 찾음")
    io.open(path, "w", encoding="utf-8", newline="").write(html)
    print("갱신:", rel)
