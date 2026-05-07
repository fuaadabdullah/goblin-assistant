#!/usr/bin/env python3
"""
Fix production environment variables on Render:
1. Generate and set LOCAL_LLM_API_KEY (critical auth)
2. Fix GROQ_ENDPOINT (should be https://api.groq.com/openai)
3. Preserve all existing environment variables
"""

import os
import json
import yaml
import urllib.request
import ssl
import secrets
import base64

def main():
    # Generate secure LOCAL_LLM_API_KEY (32 bytes = 256 bits)
    local_llm_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    print(f"Generated LOCAL_LLM_API_KEY: {local_llm_key[:10]}...{local_llm_key[-10:]}")

    # Load Render API credentials
    config_path = os.path.expanduser('~/.render/cli.yaml')
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
    
    api_key = (config.get('api') or {}).get('key', '')
    if not api_key:
        print("❌ ERROR: No Render API key found in ~/.render/cli.yaml")
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
    
    # Show critical vars status
    critical_vars = ['JWT_SECRET_KEY', 'GROQ_API_KEY', 'ANTHROPIC_API_KEY', 'LOCAL_LLM_API_KEY']
    for var in critical_vars:
        status = "✅" if var in current_env and current_env[var] else "❌"
        print(f"   {status} {var}")

    # Prepare updated env set
    updated_env = current_env.copy()

    # 1. Add/update critical auth var
    updated_env['LOCAL_LLM_API_KEY'] = local_llm_key
    print(f"\n🔑 Setting LOCAL_LLM_API_KEY (enables API authentication)")

    # 2. Fix Groq endpoint (if GROQ_API_KEY exists)
    if 'GROQ_API_KEY' in updated_env and updated_env['GROQ_API_KEY']:
        updated_env['GROQ_ENDPOINT'] = 'https://api.groq.com/openai'
        print(f"🔧 Fixed GROQ_ENDPOINT → https://api.groq.com/openai")
    
    # 3. Check DATABASE_URL status
    if 'DATABASE_URL' not in updated_env or not updated_env['DATABASE_URL']:
        print(f"ℹ️  DATABASE_URL not set (app will use SQLite fallback)")

    # Prepare payload for Render API (PUT replaces all vars)
    env_vars_payload = [{"key": k, "value": v} for k, v in updated_env.items()]

    # Save to file for review/debugging
    output_file = '/tmp/render_env_update_payload.json'
    with open(output_file, 'w') as f:
        json.dump(env_vars_payload, f, indent=2)

    print(f"\n✅ Prepared {len(env_vars_payload)} environment variables")
    print(f"   Payload saved to: {output_file}")
    
    # Apply update to Render
    print(f"\n🚀 Applying environment variable updates to Render...")
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
            response = json.loads(r.read().decode())
            print(f"✅ Environment variables updated successfully!")
            return 0
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ Failed to update environment variables:")
        print(f"   Status: {e.code}")
        print(f"   Response: {error_body}")
        return 1

if __name__ == '__main__':
    exit(main())
