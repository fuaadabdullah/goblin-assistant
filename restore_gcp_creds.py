#!/usr/bin/env python3
"""Add GCP credentials to Render env vars."""

import json
import urllib.request
import ssl

# Load GCP credentials from temp file
with open("/tmp/gcp_creds.json") as f:
    creds = json.load(f)

api_key = "rnd_ml93RHS8wrm4cLYYLLso75DNjoDi"
service_id = "srv-d4klibc9c44c73f1jh00"
ctx = ssl._create_unverified_context()

# Fetch current env vars from Render
req = urllib.request.Request(
    f"https://api.render.com/v1/services/{service_id}/env-vars",
    headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
)
with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
    data = json.loads(r.read().decode())

# Convert to key-value dict
kv = {}
for item in data:
    e = item.get("envVar", {})
    k = e.get("key")
    if k:
        kv[k] = e.get("value") or ""

# Add GCP credentials
kv["GCP_SERVICE_ACCOUNT_KEY"] = creds["adc_b64"]
kv["GOOGLE_APPLICATION_CREDENTIALS"] = creds["adc_str"]

print(f"Total env vars: {len(kv)}")
print(f"✅ Added GCP_SERVICE_ACCOUNT_KEY (base64, len={len(creds['adc_b64'])})")
print(f"✅ Added GOOGLE_APPLICATION_CREDENTIALS (JSON, len={len(creds['adc_str'])})")

# Upload to Render
payload = [{"key": k, "value": v} for k, v in kv.items()]
put_req = urllib.request.Request(
    f"https://api.render.com/v1/services/{service_id}/env-vars",
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
    print(f"✅ Synced {len(payload)} env vars to Render")
