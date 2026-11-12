# design/ — 문서 HTML 공통 테마

[theme.css](theme.css)가 원본. 색·글꼴·모서리는 웹사이트(`apps/web-platform/src/styles.css`)와 같은 값, 다크 모드 없음(웹사이트와 같음).

각 HTML에는 theme.css가 **통째로 들어가 있음** (`<!-- theme:begin -->` ~ `<!-- theme:end -->`) — 파일 미리보기·첨부로 열면 상대 경로 CSS를 못 찾아 그림이 검게 나오기 때문. theme.css를 고친 뒤에는 저장소 맨 위에서 `python design/inline_theme.py`를 돌려 다섯 장을 갱신.

| 토큰 | 값 | 쓰는 곳 |
|---|---|---|
| `--bg` · `--surface` | #f6f8fb · #ffffff | 배경 · 카드 (웹사이트와 같음) |
| `--accent` · `--accent-soft` | #1f6feb · #e3edfd | 강조 · 단계 헤더 · 칩 (웹사이트와 같음) |
| `--pain` | #d6336c | Top 3 · 감정 최저점 · 손 넘김 · 예외 분기 |
| `--assume` | #b26a00 | 가정값 · [가정] |
| `--good` | #2b8a3e | 기회 · 학습 루프 |
| `--neutral` | #8a94a3 | 보류 · 범위 밖 |
| 글꼴 | Pretendard | 웹사이트와 같음 |

적용된 파일: painpoint/journey_map.html · journey_3actors.html · priority.html · bm/bm_canvas.html · spec/userflow.html (모두 1280×720 한 장)
