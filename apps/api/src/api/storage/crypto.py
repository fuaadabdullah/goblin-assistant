"""Small helpers for encrypting durable secret material."""

from __future__ import annotations

import base64
import hashlib
import os
from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


def _derive_fernet_key(raw_secret: str) -> bytes:
    digest = hashlib.sha256(raw_secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache(maxsize=1)
def get_fernet() -> Fernet:
    seed = (
        os.getenv("API_KEY_ENCRYPTION_KEY")
        or os.getenv("SETTINGS_ENCRYPTION_KEY")
        or os.getenv("SECRET_KEY")
        or os.getenv("JWT_SECRET_KEY")
        or "goblin-assistant-dev-key"
    )
    return Fernet(_derive_fernet_key(seed))


def encrypt_secret(value: str) -> str:
    return get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> Optional[str]:
    try:
        return get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None
