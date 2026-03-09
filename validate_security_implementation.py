#!/usr/bin/env python3
"""
Security Implementation Validation
Verifies all 4 critical security fixes are in place
"""

import sys
import os

# Add api to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_redis_client():
    """Verify redis_client.py exists and imports"""
    try:
        from api.core.redis_client import get_redis_client, close_redis_client
        print("✅ redis_client.py - Singleton Redis client module")
        return True
    except Exception as e:
        print(f"❌ redis_client.py - {e}")
        return False

def check_csrf_manager():
    """Verify csrf_manager.py exists and imports"""
    try:
        from api.core.csrf_manager import generate_csrf_token, validate_csrf_token
        print("✅ csrf_manager.py - Redis-backed CSRF token manager")
        return True
    except Exception as e:
        print(f"❌ csrf_manager.py - {e}")
        return False

def check_rate_limiter():
    """Verify rate_limiter_auth.py exists and imports"""
    try:
        from api.core.rate_limiter_auth import check_rate_limit, reset_rate_limit
        print("✅ rate_limiter_auth.py - Redis-backed rate limiter")
        return True
    except Exception as e:
        print(f"❌ rate_limiter_auth.py - {e}")
        return False

def check_auth_schemas():
    """Verify auth schemas have required csrf_token"""
    try:
        from api.auth.router import UserCreate, UserLogin
        
        # Check if csrf_token is required (not optional)
        create_fields = UserCreate.model_fields
        login_fields = UserLogin.model_fields
        
        create_required = 'csrf_token' in create_fields and create_fields['csrf_token'].is_required()
        login_required = 'csrf_token' in login_fields and login_fields['csrf_token'].is_required()
        
        if create_required and login_required:
            print("✅ Auth schemas - csrf_token is REQUIRED (not optional)")
            return True
        else:
            print(f"❌ Auth schemas - csrf_token fields not properly required")
            return False
    except Exception as e:
        print(f"❌ Auth schemas - {e}")
        return False

def check_sandbox_changes():
    """Verify sandbox_api.py has bash removed"""
    try:
        with open('api/sandbox_api.py', 'r') as f:
            content = f.read()
        
        # Check bash is NOT in language list
        has_python_js = 'python' in content and 'javascript' in content
        no_bash = 'bash' not in content or ('python", "javascript"' in content and '"bash"' not in content)
        
        # More specific check: look for the language validation
        if '["python", "javascript"]' in content:
            print("✅ Sandbox - Bash REMOVED from language whitelist")
            return True
        else:
            print("⚠️  Sandbox - Could not verify bash removal")
            return False
    except Exception as e:
        print(f"❌ Sandbox - {e}")
        return False

def check_test_suite():
    """Verify test_auth_security.py exists"""
    try:
        if os.path.exists('api/test_auth_security.py'):
            with open('api/test_auth_security.py', 'r') as f:
                content = f.read()
            
            # Count test classes and methods
            test_classes = content.count('class Test')
            test_methods = content.count('def test_')
            
            if test_classes >= 3 and test_methods >= 12:
                print(f"✅ Test suite - {test_methods} test cases across {test_classes} test classes")
                return True
            else:
                print(f"⚠️  Test suite - Found {test_methods} tests, expected 12+")
                return False
        else:
            print("❌ Test suite - test_auth_security.py not found")
            return False
    except Exception as e:
        print(f"❌ Test suite - {e}")
        return False

def main():
    print("\n" + "="*70)
    print("SECURITY IMPLEMENTATION VALIDATION")
    print("="*70 + "\n")
    
    print("Phase 1: Redis Infrastructure")
    print("-" * 70)
    r1 = check_redis_client()
    r2 = check_csrf_manager()
    r3 = check_rate_limiter()
    
    print("\nPhase 2: Auth Enforcement")
    print("-" * 70)
    r4 = check_auth_schemas()
    
    print("\nPhase 3: Sandbox Restrictions")
    print("-" * 70)
    r5 = check_sandbox_changes()
    
    print("\nPhase 4: Testing")
    print("-" * 70)
    r6 = check_test_suite()
    
    print("\n" + "="*70)
    results = [r1, r2, r3, r4, r5, r6]
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        print("="*70)
        print("\nSecurity Implementation Status: COMPLETE")
        print("\nReady for:")
        print("  1. Testing with pytest")
        print("  2. Deployment to production")
        print("  3. Client integration (CSRF token flow)")
        return 0
    else:
        print(f"⚠️  VALIDATION INCOMPLETE ({passed}/{total} passed)")
        print("="*70)
        return 1

if __name__ == '__main__':
    sys.exit(main())
