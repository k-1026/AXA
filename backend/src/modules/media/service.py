"""사진·영상 저장소 (A). Supabase Storage 비공개 버킷에 서명된 주소로 올리고 본다.

- 파일은 서버를 거치지 않음: 서버가 서명된 업로드 주소를 주고, 브라우저가 Supabase로 바로 PUT (Vercel 요청 크기 제한 피함)
- 볼 때도 서명된 주소(1시간)만 줌 → 버킷은 공개하지 않음. 누구에게 줄지는 부르는 쪽(aftercare)이 권한 확인 뒤 결정
- 서비스 키는 서버 전용 (core/config.py). 설정이 없으면 `enabled() = False` → 업로드 API는 503 `storage.unavailable`
"""

import re
import uuid

import httpx

from core.config import get_settings
from core.errors import AppError

BUCKET = "aftercare-media"
MAX_BYTES = 50 * 1024 * 1024  # 1개 50MB (환자 화면 안내와 같음, Supabase 무료 플랜 파일 상한)
VIEW_SECONDS = 3600
KINDS = ("image", "video")
TIMEOUT = 10.0


def enabled() -> bool:
    s = get_settings()
    return bool(s.supabase_url and s.supabase_service_role_key)


def _base() -> str:
    return get_settings().supabase_url.rstrip("/") + "/storage/v1"


def _headers() -> dict:
    key = get_settings().supabase_service_role_key
    return {"Authorization": f"Bearer {key}", "apikey": key}


def _unavailable() -> AppError:
    return AppError(503, "storage.unavailable", "사진·영상 저장소를 쓸 수 없습니다")


def _full(url: str) -> str:
    return url if url.startswith("http") else _base() + (url if url.startswith("/") else "/" + url)


def kind_of(content_type: str) -> str | None:
    head = (content_type or "").split("/")[0]
    return head if head in KINDS else None


def new_path(prefix: str, name: str) -> str:
    """`{prefix}/{무작위}.{확장자}` — 원래 파일 이름은 경로에 넣지 않음 (이름에 개인정보가 있을 수 있음)."""
    m = re.search(r"\.([A-Za-z0-9]{1,5})$", name or "")
    return f"{prefix}/{uuid.uuid4().hex}" + (f".{m.group(1).lower()}" if m else "")


def sign_upload(path: str) -> str:
    """한 번 쓰는 업로드 주소 (브라우저가 이 주소로 파일을 PUT)."""
    if not enabled():
        raise _unavailable()
    try:
        r = httpx.post(f"{_base()}/object/upload/sign/{BUCKET}/{path}", headers=_headers(), timeout=TIMEOUT)
        r.raise_for_status()
        return _full(r.json()["url"])
    except (httpx.HTTPError, KeyError, ValueError):
        raise _unavailable()


def sign_views(paths: list[str]) -> dict[str, str]:
    """경로 → 볼 수 있는 주소 (1시간). 실패하면 빈 값 → 화면은 "사진 있음"만 표시."""
    paths = [p for p in dict.fromkeys(paths) if p]
    if not paths or not enabled():
        return {}
    try:
        r = httpx.post(f"{_base()}/object/sign/{BUCKET}", headers=_headers(),
                       json={"expiresIn": VIEW_SECONDS, "paths": paths}, timeout=TIMEOUT)
        r.raise_for_status()
        return {x["path"]: _full(x["signedURL"]) for x in r.json() if x.get("signedURL")}
    except (httpx.HTTPError, KeyError, ValueError, TypeError):
        return {}


def attachments_out(messages) -> dict[int, list[dict]]:
    """메시지 id → [{kind, name, url}] (url은 1시간, 못 만들면 None → 화면은 "사진 있음"만)."""
    urls = sign_views([a.get("path") for m in messages for a in (m.attachments or [])])
    return {
        m.id: [{"kind": a.get("kind"), "name": a.get("name"), "url": urls.get(a.get("path"))} for a in (m.attachments or [])]
        for m in messages
    }
