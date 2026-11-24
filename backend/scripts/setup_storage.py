"""Supabase Storage 비공개 버킷 `aftercare-media` 만들기 (한 번만, 이미 있으면 설정만 맞춤).

실행 (저장소 루트, .env에 SUPABASE_URL·SUPABASE_SERVICE_ROLE_KEY):
    uv run python backend/scripts/setup_storage.py

- public = false (주소를 알아도 못 봄, 서명된 주소로만)
- 파일 1개 50MB, 사진·영상만
"""

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.config import get_settings  # noqa: E402
from modules.media.service import BUCKET, MAX_BYTES, headers  # noqa: E402

CONFIG = {"public": False, "file_size_limit": MAX_BYTES, "allowed_mime_types": ["image/*", "video/*"]}


def main() -> int:
    s = get_settings()
    if not (s.supabase_url and s.supabase_service_role_key):
        print("SUPABASE_URL·SUPABASE_SERVICE_ROLE_KEY가 .env에 없어요")
        return 1
    if s.supabase_service_role_key.startswith("sb_publishable_"):
        print("SUPABASE_SERVICE_ROLE_KEY에 공개 키(sb_publishable_)가 들어 있어요 → 비밀 키(sb_secret_ 또는 service_role)로 바꿔 주세요")
        return 1
    base = s.supabase_url.rstrip("/") + "/storage/v1"
    h = headers(s.supabase_service_role_key)
    r = httpx.get(f"{base}/bucket/{BUCKET}", headers=h, timeout=15)
    if r.status_code == 200:
        r = httpx.put(f"{base}/bucket/{BUCKET}", headers=h, json=CONFIG, timeout=15)
        action = "설정 맞춤"
    else:
        r = httpx.post(f"{base}/bucket", headers=h, json={"id": BUCKET, "name": BUCKET, **CONFIG}, timeout=15)
        action = "만듦"
    if r.status_code >= 300:
        print(f"실패 {r.status_code}: {r.text[:200]}")
        return 1
    info = httpx.get(f"{base}/bucket/{BUCKET}", headers=h, timeout=15).json()
    print(f"버킷 {BUCKET} {action}: public={info.get('public')} limit={info.get('file_size_limit')} types={info.get('allowed_mime_types')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
