"""Lightweight monitoring server for Celery/Redis health in docker-compose."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import redis

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
HOST = os.getenv("CELERY_MONITOR_HOST", "0.0.0.0")
PORT = int(os.getenv("CELERY_MONITOR_PORT", "5555"))


def _check_redis(url: str) -> tuple[bool, str]:
    try:
        parsed = urlparse(url)
        client = redis.Redis(
            host=parsed.hostname or "redis",
            port=parsed.port or 6379,
            db=int(parsed.path.strip("/") or "0"),
            username=parsed.username,
            password=parsed.password,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        pong = client.ping()
        if pong:
            return True, "ok"
        return False, "ping_failed"
    except Exception as exc:
        return False, str(exc)


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path not in {"/health", "/healthz"}:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")
            return

        ok, detail = _check_redis(BROKER_URL)
        status_code = 200 if ok else 503
        payload = {
            "status": "healthy" if ok else "unhealthy",
            "broker": BROKER_URL,
            "detail": detail,
        }
        body = json.dumps(payload).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), _Handler)
    server.serve_forever()
