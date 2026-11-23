"""웹 푸시 VAPID 키 한 쌍 만들기 (결정 30). 출력된 두 줄을 루트 .env에 붙여 넣음 (커밋 X, 배포는 Vercel 환경변수).

    uv run --no-sync python backend/scripts/make_vapid_keys.py

키를 바꾸면 기존 구독은 모두 다시 해야 함 (브라우저가 새 공개 키로 다시 구독).
"""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


key = ec.generate_private_key(ec.SECP256R1())
private = key.private_numbers().private_value.to_bytes(32, "big")
public = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
print(f"VAPID_PUBLIC_KEY={b64(public)}")
print(f"VAPID_PRIVATE_KEY={b64(private)}")
