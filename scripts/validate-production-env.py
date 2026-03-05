#!/usr/bin/env python3
"""
Production Environment Validation Script
Validates that all required environment variables are set for production deployment
"""

import os
import sys
from typing import List, Dict
from dotenv import load_dotenv


def load_env_file(env_file: str = None):
    """Load environment variables from file"""
    if env_file:
        if os.path.exists(env_file):
            load_dotenv(env_file)
            print(f"✅ Loaded environment from: {env_file}")
        else:
            print(f"❌ Environment file not found: {env_file}")
            sys.exit(1)


def validate_production_env() -> Dict[str, List[str]]:
    """Validate production environment configuration"""
    errors = []
    warnings = []

    # Required production variables
    required_vars = [
        "DATABASE_URL",
        "JWT_SECRET_KEY",
        "ENVIRONMENT",
        "ALLOWED_ORIGINS",
        "LOCAL_LLM_API_KEY",
    ]

    # Check required variables
    for var in required_vars:
        if not os.getenv(var):
            errors.append(f"❌ Missing required variable: {var}")
        else:
            print(f"✅ {var} is set")

    # Check environment is production
    env = os.getenv("ENVIRONMENT", "").lower()
    if env != "production":
        warnings.append(
            f"⚠️  ENVIRONMENT is '{env}', should be 'production' for production deployment"
        )

    # Check debug is disabled
    debug = os.getenv("DEBUG", "false").lower()
    if debug == "true":
        errors.append("❌ DEBUG is enabled in production - set DEBUG=false")

    # Check CORS is configured
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "")
    if not allowed_origins:
        errors.append("❌ ALLOWED_ORIGINS not configured for production CORS")

    # Check database URL doesn't contain obvious placeholders
    db_url = os.getenv("DATABASE_URL", "")
    if "your_" in db_url.lower() or "placeholder" in db_url.lower():
        errors.append("❌ DATABASE_URL contains placeholder values")

    # Check JWT secret is not default
    jwt_secret = os.getenv("JWT_SECRET_KEY", "")
    if not jwt_secret or len(jwt_secret) < 32:
        errors.append(
            "❌ JWT_SECRET_KEY is too short or not set (minimum 32 characters)"
        )

    # Check API keys are not placeholders (warnings only)
    api_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_AI_API_KEY"]

    for key in api_keys:
        value = os.getenv(key, "")
        if value and ("your_" in value.lower() or "placeholder" in value.lower()):
            warnings.append(f"⚠️  {key} contains placeholder value")

    return {"errors": errors, "warnings": warnings}


def main():
    """Main validation function"""
    # Parse command line arguments
    env_file = None
    if len(sys.argv) > 1:
        env_file = sys.argv[1]

    print("🔍 Validating Production Environment Configuration")
    if env_file:
        print(f"📄 Using environment file: {env_file}")
    print("=" * 60)

    # Load environment file if specified
    load_env_file(env_file)

    result = validate_production_env()

    if result["errors"]:
        print(f"\n❌ CRITICAL ERRORS ({len(result['errors'])}):")
        for error in result["errors"]:
            print(f"  {error}")

    if result["warnings"]:
        print(f"\n⚠️  WARNINGS ({len(result['warnings'])}):")
        for warning in result["warnings"]:
            print(f"  {warning}")

    if not result["errors"] and not result["warnings"]:
        print("\n🎉 All production environment variables are properly configured!")
        return 0
    elif result["errors"]:
        print(
            f"\n❌ {len(result['errors'])} critical errors found. Fix before deploying to production."
        )
        return 1
    else:
        print(
            f"\n⚠️  {len(result['warnings'])} warnings found. Review before deploying to production."
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
