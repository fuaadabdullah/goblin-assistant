#!/usr/bin/env python3
"""
URGENT: Add JWT_SECRET_KEY to Render environment variables.
The previous update accidentally removed JWT_SECRET_KEY, causing backend startup failure.
"""

import os
import json
import yaml
import urllib.request
import ssl
import secrets
import base64

def main():
    # Generate secure JWT_SECRET_KEY (64 bytes = 512 bits for extra security)
    jwt_secret_key = base64.urlsafe_b64encode(secrets.token_bytes(64)).decode('utf-8').rstrip('=')
    print(f"Generated JWT_SECRET_KEY: {jwt_secret_key[:15]}...{jwt_secret_key[-15:]}")

    # Load Render API credentials
    config_path = os.path.expanduser('~/.render/cli.yaml')
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
    
    api_key = (config.get('api') or {}).get('key', '')
    if not api_key:
        print("❌ ERROR: No Render API key found")
        return 1

    # Fetch current env vars from Render
    print("\n📥 Fetching current environment variables from Render...")
    ctx = ssl._create_unverified_context()
    req = urllib.request.Request(
        'https://api.render.com/v1/services/srv-d4klibc9c44c73f1jh00/env-vars',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Accept': 'application/json'
        }
    )

    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        current_data = json.loads(r.read().decode())

    # Extract current env vars
    current_env = {}
    for item in current_data:
        if isinstance(item, dict) and 'envVar' in item:
            key = item['envVar'].get('key', '')
            value = item['envVar'].get('value', '')
            if key:
                current_env[key] = value

    print(f"   Found {len(current_env)} existing environment variables")
    print(f"   Has JWT_SECRET_KEY: {'✅' if 'JWT_SECRET_KEY' in current_env else '❌ MISSING'}")
    print(f"   Has LOCAL_LLM_API_KEY: {'✅' if 'LOCAL_LLM_API_KEY' in current_env else '❌'}")

    # Add JWT_SECRET_KEY
    updated_env = current_env.copy()
    updated_env['JWT_SECRET_KEY'] = jwt_secret_key
    print(f"\n🔑 Adding JWT_SECRET_KEY (CRITICAL for backend startup)")

    # Prepare payload
    env_vars_payload = [{"key": k, "value": v} for k, v in updated_env.items()]

    print(f"\n✅ Prepared {len(env_vars_payload)} environment variables")
    print(f"   Total keys: {len(updated_env)}")
    
    # Apply update to Render
    print(f"\n🚀 Applying JWT_SECRET_KEY to Render...")
    put_req = urllib.request.Request(
        'https://api.render.com/v1/services/srv-d4klibc9c44c73f1jh00/env-vars',
        data=json.dumps(env_vars_payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        method='PUT'
    )

    try:
        with urllib.request.urlopen(put_req, timeout=30, context=ctx) as r:
            _ = r.read()
            print("✅ JWT_SECRET_KEY added successfully!")
            print("\n⚠️  YOU MUST REDEPLOY THE BACKEND FOR THIS TO TAKE EFFECT")
            return 0
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ Failed to update environment variables:")
        print(f"   Status: {e.code}")
        print(f"   Response: {error_body}")
        return 1

if __name__ == '__main__':
    exit(main())
