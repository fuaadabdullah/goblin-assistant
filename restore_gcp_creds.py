#!/usr/bin/env python3
"""Securely add GCP credentials to Render env vars.

This script intentionally avoids embedding secrets in the repository. It reads
the Render API key and service ID from environment variables:

  - RENDER_API_KEY
  - RENDER_SERVICE_ID

It also expects a local GCP creds file at `/tmp/gcp_creds.json` (not checked in)
that contains `adc_b64` and `adc_str` fields.
"""

import json
import os
import sys
import urllib.request
import ssl


# Load GCP credentials from temp file
creds_path = os.getenv("GCP_CREDS_PATH", "/tmp/gcp_creds.json")
if not os.path.exists(creds_path):
    print(f"Error: GCP credentials file not found at {creds_path}")
    print("Place your GCP creds JSON at that path or set GCP_CREDS_PATH environment variable.")
    sys.exit(1)

with open(creds_path) as f:
    creds = json.load(f)

# Read Render credentials from environment (do NOT store API keys in repo)
api_key = os.getenv("RENDER_API_KEY")
service_id = os.getenv("RENDER_SERVICE_ID")
if not api_key or not service_id:
    print("Error: RENDER_API_KEY and RENDER_SERVICE_ID must be set as environment variables.")
    print("Example (local): export RENDER_API_KEY=...; export RENDER_SERVICE_ID=...")
    sys.exit(1)

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
    # Render returns items with a top-level "envVar" key
    e = item.get("envVar", {})
    k = e.get("key")
    if k:
        kv[k] = e.get("value") or ""

# Add GCP credentials
kv["GCP_SERVICE_ACCOUNT_KEY"] = creds.get("adc_b64", "")
kv["GOOGLE_APPLICATION_CREDENTIALS"] = creds.get("adc_str", "")

print(f"Total env vars to sync: {len(kv)}")
print("✅ Added GCP_SERVICE_ACCOUNT_KEY and GOOGLE_APPLICATION_CREDENTIALS (lengths hidden)")

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
