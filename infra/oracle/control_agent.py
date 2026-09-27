from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def _run(argv: list[str], timeout: float = 5.0) -> dict[str, object]:
    try:
        proc = subprocess.run(argv, check=False, capture_output=True, text=True, timeout=timeout)
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-16000:],
            "stderr": proc.stderr[-4000:],
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def host_status() -> dict[str, object]:
    load = Path("/proc/loadavg").read_text().split()[:3]
    mem: dict[str, str] = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
            mem[key] = value.strip()
    root = shutil.disk_usage("/")
    return {
        "read_only": True,
        "uptime_seconds": time.monotonic(),
        "load_average": load,
        "memory": mem,
        "root_disk": {
            "total_bytes": root.total,
            "used_bytes": root.used,
            "free_bytes": root.free,
        },
    }


def docker_status() -> dict[str, object]:
    ps = _run(["docker", "ps", "--no-trunc", "--format", "{{json .}}"])
    containers: list[dict[str, object]] = []
    if ps.get("ok"):
        for line in str(ps.get("stdout", "")).splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                containers.append(value)
    return {
        "read_only": True,
        "docker_available": shutil.which("docker") is not None,
        "containers": containers[:100],
        "command_ok": ps.get("ok", False),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(200, {"ok": True, "read_only": True})
        elif self.path == "/v1/status":
            self._json(200, host_status())
        elif self.path == "/v1/docker":
            self._json(200, docker_status())
        else:
            self._json(404, {"error": "not_found"})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=18091)
    args = parser.parse_args()
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
