#!/usr/bin/env python3
"""Sync updated ADC credentials (with quota project) to Render."""

import os
import json
import yaml
import urllib.request
import ssl
import base64

# Read updated ADC credentials
with open(os.path.expanduser("~/.config/gcloud/application_default_credentials.json")) as f:
    adc_json = json.load(f)

# Encode as base64 for safe env var transport
adc_b64 = base64.b64encode(json.dumps(adc_json).encode()).decode()

# Get Render API key
cfg = yaml.safe_load(open(os.path.expanduser("~/.render/cli.yaml"))) or {}
api_key = (cfg.get("api") or {}).get("key", "")

# Fetch current env vars
ctx = ssl._create_unverified_context()
req = urllib.request.Request(
    "https://api.render.com/v1/services/srv-d4klibc9c44c73f1jh00/env-vars",
    headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
)
with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
    data = json.loads(r.read().decode())

kv = {}
for it in data:
    e = (it or {}).get("envVar", {})
    k = e.get("key")
    if k:
        kv[k] = e.get("value") or ""

# Update with new ADC (base64)
kv["GCP_SERVICE_ACCOUNT_KEY"] = adc_b64
print(f"Updating GCP_SERVICE_ACCOUNT_KEY (len={len(adc_b64)} chars)")
print(f"Quota project in ADC: {adc_json.get('quota_project_id')}")

# Push update
payload = [{"key": k, "value": v} for k, v in kv.items()]
put_req = urllib.request.Request(
    "https://api.render.com/v1/services/srv-d4klibc9c44c73f1jh00/env-vars",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    },
    method="PUT",
)
with urllib.request.urlopen(put_req, timeout=30, context=ctx) as r:
    result = json.loads(r.read().decode())
    print("✅ Updated Render env vars with latest ADC credentials")
    print(f"   Total env vars now: {len(payload)}")
