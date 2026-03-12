#!/usr/bin/env python3
"""
Privacy & Security Integration Validation Script
Validates that all privacy features are correctly integrated into Goblin Assistant.
"""

import sys
import os
from pathlib import Path

# Colors for output
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
NC = "\033[0m"  # No Color


def print_success(msg):
    print(f"{GREEN}✓{NC} {msg}")


def print_error(msg):
    print(f"{RED}✗{NC} {msg}")


def print_warning(msg):
    print(f"{YELLOW}⚠{NC} {msg}")


def check_file_exists(filepath, description):
    """Check if a required file exists."""
    if Path(filepath).exists():
        print_success(f"{description}: {filepath}")
        return True
    else:
        print_error(f"{description} missing: {filepath}")
        return False


def check_import(module_path, item_name):
    """Check if a module/function can be imported."""
    try:
        parts = module_path.rsplit(".", 1)
        if len(parts) == 2:
            module_name, _ = parts
            module = __import__(module_name, fromlist=[item_name])
            getattr(module, item_name)
        else:
            __import__(module_path)
        print_success(f"Import: {module_path}.{item_name if item_name else ''}")
        return True
    except ImportError as e:
        print_error(f"Import failed: {module_path}.{item_name} - {e}")
        return False
    except AttributeError as e:
        print_error(f"Attribute error: {module_path}.{item_name} - {e}")
        return False


def check_redis_connection():
    """Check if Redis is running."""
    try:
        import redis

        r = redis.Redis(host="localhost", port=6379, db=0, socket_connect_timeout=2)
        r.ping()
        print_success("Redis connection: OK")
        return True
    except Exception as e:
        print_warning(f"Redis not available: {e}")
        print_warning("  Rate limiting will not work without Redis")
        return False


def main():
    print("=" * 70)
    print("  GOBLIN ASSISTANT - PRIVACY INTEGRATION VALIDATION")
    print("=" * 70)
    print()

    # Change to API directory
    api_dir = Path(__file__).parent.parent / "api"
    os.chdir(api_dir)
    sys.path.insert(0, str(api_dir))

    checks_passed = 0
    checks_failed = 0
    checks_warned = 0

    # Check core service files
    print("1️⃣  Checking Core Service Files...")
    files_to_check = [
        ("services/sanitization.py", "Sanitization module"),
        ("services/safe_vector_store.py", "Safe Vector Store"),
        ("services/telemetry.py", "Telemetry module"),
        ("routes/privacy.py", "Privacy routes"),
        ("middleware/rate_limiter.py", "Rate limiter"),
        (".env.privacy.example", "Environment template"),
        ("requirements.txt", "Main requirements (includes privacy deps)"),
    ]

    for filepath, desc in files_to_check:
        if check_file_exists(filepath, desc):
            checks_passed += 1
        else:
            checks_failed += 1
    print()

    # Check imports
    print("2️⃣  Checking Python Imports...")
    imports_to_check = [
        ("services.sanitization", "sanitize_input_for_model"),
        ("services.sanitization", "is_sensitive_content"),
        ("services.sanitization", "mask_sensitive"),
        ("services.telemetry", "log_inference_metrics"),
        ("middleware.rate_limiter", "RateLimiter"),
    ]

    for module, item in imports_to_check:
        if check_import(module, item):
            checks_passed += 1
        else:
            checks_failed += 1
    print()

    # Check Redis
    print("3️⃣  Checking External Dependencies...")
    if check_redis_connection():
        checks_passed += 1
    else:
        checks_warned += 1
    print()

    # Check main.py integration
    print("4️⃣  Checking main.py Integration...")
    try:
        with open("main.py", "r") as f:
            main_content = f.read()

        integrations = [
            ("privacy_router", "Privacy router import"),
            ("RateLimiter", "Rate limiter import"),
            ("app.include_router", "Router includes"),
        ]

        for pattern, desc in integrations:
            if pattern in main_content:
                print_success(f"{desc}: Found")
                checks_passed += 1
            else:
                print_warning(f"{desc}: Not found (optional)")
                checks_warned += 1
    except Exception as e:
        print_error(f"Failed to check main.py: {e}")
        checks_failed += 1
    print()

    # Run sanitization tests
    print("5️⃣  Running Sanitization Tests...")
    try:
        from services.sanitization import sanitize_input_for_model, is_sensitive_content

        # Test 1: Email
        text = "test@example.com"
        sanitized, pii = sanitize_input_for_model(text)
        if "REDACTED" in sanitized and "email" in pii:
            print_success("Email sanitization: PASS")
            checks_passed += 1
        else:
            print_error("Email sanitization: FAIL")
            checks_failed += 1

        # Test 2: Sensitive content
        if is_sensitive_content("password: secret123"):
            print_success("Sensitive content detection: PASS")
            checks_passed += 1
        else:
            print_error("Sensitive content detection: FAIL")
            checks_failed += 1

    except Exception as e:
        print_error(f"Sanitization tests failed: {e}")
        checks_failed += 2
    print()

    # Check documentation
    print("6️⃣  Checking Documentation...")
    docs_to_check = [
        ("docs/PRIVACY_IMPLEMENTATION.md", "Implementation guide"),
        ("docs/PRIVACY_INTEGRATION_GUIDE.md", "Integration guide"),
        ("PRIVACY_QUICK_REFERENCE.md", "Quick reference"),
    ]

    for filepath, desc in docs_to_check:
        full_path = Path("..") / filepath
        if check_file_exists(str(full_path), desc):
            checks_passed += 1
        else:
            checks_warned += 1
    print()

    # Summary
    print("=" * 70)
    print("  VALIDATION SUMMARY")
    print("=" * 70)
    print(f"{GREEN}Passed:{NC}  {checks_passed}")
    print(f"{RED}Failed:{NC}  {checks_failed}")
    print(f"{YELLOW}Warnings:{NC} {checks_warned}")
    print()

    if checks_failed == 0:
        print(f"{GREEN}✅ All critical checks passed!{NC}")
        print()
        print("Next steps:")
        print("  1. Review deployment checklist in PRIVACY_IMPLEMENTATION_COMPLETE.md")
        print("  2. Configure .env from .env.privacy.example")
        print("  3. Run: pytest tests/test_privacy_integration.py")
        print("  4. Deploy Supabase migrations")
        print("  5. Deploy to staging")
        return 0
    else:
        print(f"{RED}❌ Some checks failed. Fix issues before deploying.{NC}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
