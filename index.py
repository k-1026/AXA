"""Vercel 백엔드 진입 파일 (A). Vercel FastAPI는 저장소 루트의 `index.py`에서 `app`을 찾는다.

백엔드 코드는 `backend/src`(core·modules)와 저장소 루트(ai/)를 같이 불러오므로, 경로를 먼저 넣고 `main.app`을 내보낸다.
로컬 실행은 그대로: `uv run python -m uvicorn main:app --app-dir backend/src` (docs/deploy-vercel.md)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for p in (ROOT / "backend" / "src", ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from main import app  # noqa: E402,F401
