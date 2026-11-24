"""사진·영상 저장소 (A). Supabase Storage 비공개 버킷에 서명된 주소로 올리고 본다.

- 파일은 서버를 거치지 않음: 서버가 서명된 업로드 주소를 주고, 브라우저가 Supabase로 바로 PUT (Vercel 요청 크기 제한 피함)
- 볼 때도 서명된 주소(1시간)만 줌 → 버킷은 공개하지 않음. 누구에게 줄지는 부르는 쪽(aftercare)이 권한 확인 뒤 결정
- 서비스 키는 서버 전용 (core/config.py). 설정이 없으면 `enabled() = False` → 업로드 API는 503 `storage.unavailable`
- 지우기: 탈퇴 때 그 환자 파일 바로(`remove`), 그 밖에 DB에 없는 파일은 정기 정리가 하루 뒤(`list_objects` → `remove`)
- 사진 썸네일(결정 29): 브라우저가 줄인 사진과 작은 썸네일을 같이 올림. 썸네일 경로는 원본 경로에서 정해짐(`thumb_path`)
  → DB에는 `thumb: true`만, 지우기·정기 정리는 원본 경로로 썸네일도 같이 다룸
"""

from datetime import datetime

import re
import uuid

import httpx

from core.config import get_settings
from core.errors import AppError

BUCKET = "aftercare-media"
MAX_BYTES = 50 * 1024 * 1024  # 1개 50MB (환자 화면 안내와 같음, Supabase 무료 플랜 파일 상한)
VIEW_SECONDS = 3600
THUMB_SUFFIX = ".thumb.jpg"
KINDS = ("image", "video")
TIMEOUT = 10.0


def enabled() -> bool:
    s = get_settings()
    return bool(s.supabase_url and s.supabase_service_role_key)


def _base() -> str:
    return get_settings().supabase_url.rstrip("/") + "/storage/v1"


def headers(key: str) -> dict:
    """새 형식 비밀 키(`sb_secret_…`)는 JWT가 아니라 `apikey`로만, 예전 service_role 키(JWT)는 Bearer도 같이."""
    return {"apikey": key} if key.startswith("sb_") else {"Authorization": f"Bearer {key}", "apikey": key}


def _headers() -> dict:
    return headers(get_settings().supabase_service_role_key)


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


def thumb_path(path: str) -> str:
    """원본 경로 → 썸네일 경로 (`a/b/c.jpg` → `a/b/c.thumb.jpg`). 같은 폴더라 권한·정리 규칙이 그대로."""
    return re.sub(r"\.[A-Za-z0-9]{1,5}$", "", path) + THUMB_SUFFIX


def with_thumbs(paths: list[str]) -> list[str]:
    """지울 때: 원본마다 썸네일 경로도 (없는 파일을 지워도 Storage는 오류 없이 넘어감)."""
    return [x for p in paths if p for x in (p, thumb_path(p))]


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
    """메시지 id → [{kind, name, url, thumb_url}] (1시간, 못 만들면 None → 화면은 "사진 있음"만, 썸네일이 없으면 원본)."""
    atts = [a for m in messages for a in (m.attachments or [])]
    urls = sign_views([a.get("path") for a in atts] + [thumb_path(a["path"]) for a in atts if a.get("thumb") and a.get("path")])

    def one(a: dict) -> dict:
        thumb = urls.get(thumb_path(a["path"])) if a.get("thumb") and a.get("path") else None
        return {"kind": a.get("kind"), "name": a.get("name"), "url": urls.get(a.get("path")), "thumb_url": thumb}

    return {m.id: [one(a) for a in (m.attachments or [])] for m in messages}


def remove(paths: list[str]) -> int:
    """파일 지우기 → 지운 수. 실패하면 0 (DB에서 빠진 파일은 정기 정리가 다시 지움)."""
    paths = [p for p in dict.fromkeys(paths) if p]
    if not paths or not enabled():
        return 0
    try:
        r = httpx.request("DELETE", f"{_base()}/object/{BUCKET}", headers=_headers(), json={"prefixes": paths}, timeout=TIMEOUT)
        r.raise_for_status()
        return len(r.json())
    except (httpx.HTTPError, ValueError, TypeError):
        return 0


def list_objects(prefix: str = "", _depth: int = 0) -> list[tuple[str, datetime | None]]:
    """버킷의 모든 파일 (경로, 만든 시각). 경로가 `{tenant}/{request}/{file}`이라 폴더를 따라 내려감."""
    if not enabled() or _depth > 3:
        return []
    out: list[tuple[str, datetime | None]] = []
    offset = 0
    while True:
        r = httpx.post(f"{_base()}/object/list/{BUCKET}", headers=_headers(), timeout=TIMEOUT,
                       json={"prefix": prefix, "limit": 1000, "offset": offset, "sortBy": {"column": "name", "order": "asc"}})
        r.raise_for_status()
        items = r.json()
        for it in items:
            path = f"{prefix}/{it['name']}" if prefix else it["name"]
            if it.get("id") is None:  # 폴더
                out += list_objects(path, _depth + 1)
            else:
                ts = it.get("created_at")
                out.append((path, datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None))
        if len(items) < 1000:
            return out
        offset += 1000
