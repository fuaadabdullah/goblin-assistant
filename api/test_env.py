#!/usr/bin/env python3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Environment variables loaded:")
print(
    f"OPENAI_API_KEY: {'***' + os.getenv('OPENAI_API_KEY', '')[-4:] if os.getenv('OPENAI_API_KEY') else 'Not set'}"
)
print(
    f"ANTHROPIC_API_KEY: {'***' + os.getenv('ANTHROPIC_API_KEY', '')[-4:] if os.getenv('ANTHROPIC_API_KEY') else 'Not set'}"
)
print(
    f"GEMINI_API_KEY: {'***' + os.getenv('GEMINI_API_KEY', '')[-4:] if os.getenv('GEMINI_API_KEY') else 'Not set'}"
)

# Test FastAPI import
try:
    import importlib.util

    spec = importlib.util.find_spec("main")
    if spec is not None:
        print("FastAPI main module: AVAILABLE")
    else:
        print("FastAPI main module: NOT FOUND")
except Exception as e:
    print(f"FastAPI check: FAILED - {e}")

# Test database initialization
try:
    from app import init_db

    print("Database initialization: Starting...")
    init_db()
    print("Database initialization: OK")
except Exception as e:
    print(f"Database initialization: FAILED - {e}")
