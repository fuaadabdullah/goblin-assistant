#!/usr/bin/env python3
"""Lightweight Supabase keep-alive probe for GitHub Actions cron.

This script opens a short-lived SQL connection and runs `SELECT 1`.
It intentionally does nothing else so it stays cheap and low-risk on the
Supabase free tier.

Retries are included because free-tier projects pause after inactivity and can
take up to 30 seconds to resume. A single 10-second attempt reliably fails
against a paused project, which defeats the purpose of the keep-alive.
"""

from __future__ import annotations

import os
import sys
import time
from urllib.parse import urlparse, urlunparse

import psycopg

_MAX_ATTEMPTS = 3
_CONNECT_TIMEOUT_S = 30
_RETRY_DELAY_S = 10


def _normalize_db_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        raise ValueError("database URL is empty")
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


def _redact_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.netloc:
        return url
    netloc = parsed.netloc
    if "@" in netloc and ":" in netloc.split("@", 1)[0]:
        userinfo, hostinfo = netloc.split("@", 1)
        username = userinfo.split(":", 1)[0]
        netloc = f"{username}:***@{hostinfo}"
    return urlunparse(parsed._replace(netloc=netloc))


def main() -> int:
    raw_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL") or ""
    if not raw_url:
        print("SUPABASE_DB_URL or DATABASE_URL is required", file=sys.stderr)
        return 2

    db_url = _normalize_db_url(raw_url)
    redacted = _redact_url(db_url)

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            with psycopg.connect(db_url, connect_timeout=_CONNECT_TIMEOUT_S, autocommit=True) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    value = cursor.fetchone()[0]
            print(f"keepalive_ok url={redacted} result={value} attempt={attempt}")
            return 0
        except Exception as exc:
            print(
                f"keepalive_attempt_failed url={redacted} attempt={attempt}/{_MAX_ATTEMPTS} error={exc}",
                file=sys.stderr,
            )
            if attempt < _MAX_ATTEMPTS:
                time.sleep(_RETRY_DELAY_S)

    print(f"keepalive_failed url={redacted} all {_MAX_ATTEMPTS} attempts exhausted", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
