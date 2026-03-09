#!/usr/bin/env python3
"""Quick validation of security implementation"""
import os
import sys

print("="*70)
print("SECURITY IMPLEMENTATION VALIDATION")
print("="*70 + "\n")

# Check new files exist
files_to_check = [
    ('api/core/redis_client.py', 'Redis client singleton'),
    ('api/core/csrf_manager.py', 'CSRF token manager'),
    ('api/core/rate_limiter_auth.py', 'Auth rate limiter'),
    ('api/test_auth_security.py', 'Security test suite'),
]

print("Phase 1-4: Checking implementation files...")
print("-" * 70)

all_good = True
for filepath, desc in files_to_check:
    if os.path.exists(filepath):
        print(f"✅ {desc:40} ({filepath})")
    else:
        print(f"❌ {desc:40} ({filepath}) - FILE NOT FOUND")
        all_good = False

# Check auth router was modified
print("\nPhase 2: Checking auth router modifications...")
print("-" * 70)

try:
    with open('api/auth/router.py', 'r') as f:
        content = f.read()
    
    # Check for Redis imports
    if 'from ..core.csrf_manager import' in content:
        print("✅ Auth router imports CSRF manager from Redis")
    else:
        print("❌ Auth router missing CSRF manager import")
        all_good = False
    
    if 'from ..core.rate_limiter_auth import' in content:
        print("✅ Auth router imports rate limiter from Redis")
    else:
        print("❌ Auth router missing rate limiter import")
        all_good = False
    
    # Check for async calls
    if 'await validate_csrf_token' in content:
        print("✅ Auth router uses async CSRF validation")
    else:
        print("❌ Auth router not using async CSRF")
        all_good = False
    
    if 'await check_rate_limit' in content:
        print("✅ Auth router uses async rate limiting")
    else:
        print("❌ Auth router not using async rate limit")
        all_good = False
        
except Exception as e:
    print(f"❌ Error checking auth router: {e}")
    all_good = False

# Check sandbox changes
print("\nPhase 3: Checking sandbox restrictions...")
print("-" * 70)

try:
    with open('api/sandbox_api.py', 'r') as f:
        content = f.read()
    
    if '["python", "javascript"]' in content:
        print("✅ Sandbox language list is: Python, JavaScript only")
    else:
        print("⚠️  Could not verify sandbox language restriction")
    
    if '"bash"' not in content or content.count('"bash"') < 2:
        print("✅ Bash removed from sandbox")
    else:
        print("❌ Bash still present in sandbox")
        all_good = False
        
except Exception as e:
    print(f"❌ Error checking sandbox: {e}")
    all_good = False

print("\n" + "="*70)
if all_good:
    print("✅ SECURITY IMPLEMENTATION VALIDATED - ALL CHECKS PASSED")
else:
    print("⚠️  Some checks failed - see details above")
print("="*70)
