#!/usr/bin/env python3
import json
import os
import ssl
import subprocess
import urllib.request
from pathlib import Path

import yaml

SERVICE_ID = "srv-d4klibc9c44c73f1jh00"


def main() -> int:
    project = subprocess.check_output(
        ["gcloud", "config", "get-value", "project"],
        text=True,
    ).strip()
    if not project:
        print("ERROR: gcloud project is empty")
        return 1

    adc_path = Path.home() / ".config/gcloud/application_default_credentials.json"
    if not adc_path.exists():
        print("ERROR: ADC file missing")
        return 1

    adc_raw = adc_path.read_text(encoding="utf-8")
    adc = json.loads(adc_raw)
    adc_type = adc.get("type")
    if adc_type not in {"authorized_user", "service_account", "external_account"}:
        print(f"ERROR: Unsupported ADC type: {adc_type}")
        return 1

    cfg = yaml.safe_load(open(os.path.expanduser("~/.render/cli.yaml"), "r", encoding="utf-8")) or {}
    api_key = (cfg.get("api") or {}).get("key", "")
    if not api_key:
        print("ERROR: Render API key missing")
        return 1

    ctx = ssl._create_unverified_context()

    get_req = urllib.request.Request(
        f"https://api.render.com/v1/services/{SERVICE_ID}/env-vars",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(get_req, timeout=30, context=ctx) as r:
        data = json.loads(r.read().decode())

    env = {}
    for item in data:
        env_var = (item or {}).get("envVar", {})
        key = env_var.get("key")
        if key:
            env[key] = env_var.get("value") or ""

    before = len(env)
    env["VERTEX_AI_PROJECT"] = project
    env["GCP_PROJECT_ID"] = project
    env["GOOGLE_APPLICATION_CREDENTIALS"] = adc_raw

    payload = [{"key": key, "value": value} for key, value in env.items()]

    put_req = urllib.request.Request(
        f"https://api.render.com/v1/services/{SERVICE_ID}/env-vars",
        data=json.dumps(payload).encode("utf-8"),
        method="PUT",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(put_req, timeout=60, context=ctx):
        pass

    print(f"UPDATED_ENV_KEYS {before} -> {len(env)}")
    print(f"SET_VERTEX_AI_PROJECT {project}")
    print(f"SET_GOOGLE_APPLICATION_CREDENTIALS_TYPE {adc_type}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
