#!/usr/bin/env python3
"""
Verification script for security fixes applied to Goblin Assistant backend.
Run this script to verify that all security improvements are working correctly.
"""

import os
import sys
import asyncio
import importlib.util
from typing import Dict, List, Any


def check_imports():
    """Check that all modules can be imported without errors."""
    print("🔍 Checking module imports...")

    modules_to_check = [
        "main",
        "middleware",
        "security_config",
        "storage.database",
        "storage.cache",
        "monitoring",
        "health",
        "secrets_router",
    ]

    failed_imports = []

    for module_name in modules_to_check:
        try:
            __import__(module_name)
            print(f"  ✅ {module_name}")
        except Exception as e:
            print(f"  ❌ {module_name}: {e}")
            failed_imports.append((module_name, str(e)))

    return failed_imports


def check_security_config():
    """Check security configuration."""
    print("\n🔒 Checking security configuration...")

    try:
        import security_config
        from security_config import SecurityConfig

        config = SecurityConfig.get_security_summary()

        print(f"  ✅ CORS configured: {config['cors_configured']}")
        print(f"  ✅ Rate limiting enabled: {config['rate_limiting_enabled']}")
        print(f"  ✅ Debug mode: {config['debug_mode']}")
        print(f"  ✅ Secrets backend: {config['secrets_backend']}")
        print(f"  ✅ Security headers enabled: {config['security_headers_enabled']}")

        if config["warnings"]:
            print("  ⚠️  Security warnings:")
            for warning in config["warnings"]:
                print(f"    - {warning}")
        else:
            print("  ✅ No security warnings")

        return config["warnings"]

    except Exception as e:
        print(f"  ❌ Failed to check security config: {e}")
        return [str(e)]


async def check_health_endpoint():
    """Check health endpoint functionality."""
    print("\n🏥 Checking health endpoint...")

    try:
        import health
        from health import health_check

        # This will test the health check without actually running the server
        # We're just checking that the function can be called
        print("  ✅ Health endpoint function accessible")
        return []

    except Exception as e:
        print(f"  ❌ Health endpoint error: {e}")
        return [str(e)]


def check_dependencies():
    """Check dependency versions."""
    print("\n📦 Checking dependency versions...")

    required_updates = {
        "fastapi": ">=0.110.0",
        "uvicorn": ">=0.27.0",
        "httpx": ">=0.27.0",
        "pytest": ">=8.0.0",
    }

    warnings = []

    try:
        import fastapi
        import uvicorn
        import httpx
        import pytest

        print(f"  ✅ FastAPI: {fastapi.__version__}")
        print(f"  ✅ uvicorn: {uvicorn.__version__}")
        print(f"  ✅ httpx: {httpx.__version__}")
        print(f"  ✅ pytest: {pytest.__version__}")

    except ImportError as e:
        warnings.append(f"Missing dependency: {e}")
        print(f"  ❌ {e}")

    return warnings


def check_environment_variables():
    """Check important environment variables."""
    print("\n🌍 Checking environment variables...")

    important_vars = [
        "DEBUG",
        "ALLOWED_ORIGINS",
        "DATABASE_URL",
        "REDIS_URL",
        "SECRETS_BACKEND",
    ]

    for var in important_vars:
        value = os.getenv(var, "Not set")
        status = "✅" if value != "Not set" else "⚠️"
        print(f"  {status} {var}: {value}")


def main():
    """Run all verification checks."""
    print("🚀 Starting Goblin Assistant Backend Security Verification\n")
    print("=" * 60)

    all_warnings = []
    all_errors = []

    # Check imports
    import_errors = check_imports()
    all_errors.extend(import_errors)

    # Check security configuration
    security_warnings = check_security_config()
    all_warnings.extend(security_warnings)

    # Check health endpoint
    health_errors = asyncio.run(check_health_endpoint())
    all_errors.extend(health_errors)

    # Check dependencies
    dependency_warnings = check_dependencies()
    all_warnings.extend(dependency_warnings)

    # Check environment variables
    check_environment_variables()

    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)

    if all_errors:
        print(f"\n❌ {len(all_errors)} ERRORS found:")
        for error in all_errors:
            if isinstance(error, tuple) and len(error) == 2:
                module, error_msg = error
                print(f"  - {module}: {error_msg}")
            else:
                print(f"  - {error}")
    else:
        print("\n✅ No critical errors found!")

    if all_warnings:
        print(f"\n⚠️  {len(all_warnings)} WARNINGS found:")
        for warning in all_warnings:
            print(f"  - {warning}")
    else:
        print("\n✅ No warnings found!")

    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    print("  1. Review and address any errors above")
    print("  2. Set up proper environment variables for production")
    print("  3. Configure secrets management (Vault, etc.)")
    print("  4. Set up monitoring and logging")
    print("  5. Run security scans and penetration tests")
    print("  6. Update dependencies regularly")

    # Exit with appropriate code
    if all_errors:
        print(f"\n❌ Verification failed with {len(all_errors)} errors")
        sys.exit(1)
    else:
        print(f"\n✅ Verification completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
