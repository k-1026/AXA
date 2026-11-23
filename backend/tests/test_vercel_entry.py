"""Vercel 진입 파일(루트 index.py)이 백엔드 app을 그대로 내보내는지 — 배포 때 FASTAPI_ENTRYPOINT_NOT_FOUND 방지."""

import importlib.util
from pathlib import Path


def test_루트_index_py가_main_app을_내보낸다():
    path = Path(__file__).resolve().parents[2] / "index.py"
    spec = importlib.util.spec_from_file_location("vercel_index", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from main import app

    assert mod.app is app
