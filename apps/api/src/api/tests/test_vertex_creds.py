#!/usr/bin/env python3
"""Test if ADC credentials work with google.auth and Vertex API."""

import json
import os
import base64
from pathlib import Path

# Read ADC with quota project
with open(os.path.expanduser("~/.config/gcloud/application_default_credentials.json")) as f:
    adc = json.load(f)

print(f"ADC quota_project_id: {adc.get('quota_project_id')}")

# Write to temp file like vertex provider does
tmpfile = Path("/tmp/test_vertex_creds.json")
tmpfile.write_text(json.dumps(adc), encoding="utf-8")
os.chmod(tmpfile, 0o600)

# Set env var like vertex provider
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(tmpfile)

# Now try to get access token like vertex provider does
try:
    import google.auth
    import google.auth.transport.requests
    
    creds, project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    request = google.auth.transport.requests.Request()
    creds.refresh(request)
    
    print(f"✅ Got access token: {creds.token[:50]}...")
    print(f"Project discovered: {project}")
    
    # Check quota project
    if hasattr(creds, 'quota_project_id'):
        print(f"Quota project from creds: {creds.quota_project_id}")
    else:
        print("⚠️  No quota_project_id attribute on credentials")
    
except Exception as e:
    import traceback
    print(f"❌ Error getting token: {e}")
    traceback.print_exc()

# Now test Vertex API access
print("\n=== Testing Vertex API Access ===")
try:
    import httpx
    
    # Reload creds to get fresh token
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    request = google.auth.transport.requests.Request()
    creds.refresh(request)
    
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
        "x-goog-user-project": "goblin-assistant-479511",
    }
    
    body = {
        "contents": [{"role": "user", "parts": [{"text": "ping"}]}],
        "generationConfig": {"maxOutputTokens": 1},
    }
    
    endpoint = "https://us-central1-aiplatform.googleapis.com/v1/projects/goblin-assistant-479511/locations/us-central1/publishers/google/models/gemini-1.5-flash-001:generateContent"
    
    resp = httpx.post(endpoint, headers=headers, json=body, timeout=10)
    print(f"Vertex API Response: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Error: {resp.text[:200]}")
    else:
        print("✅ Vertex API call successful!")
        
except Exception as e:
    import traceback
    print(f"❌ Vertex API error: {e}")
    traceback.print_exc()
