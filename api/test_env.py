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

# Test Flask import
try:
    from flask import Flask

    print("Flask import: OK")
except ImportError as e:
    print(f"Flask import: FAILED - {e}")

# Test database initialization
try:
    from app import init_db

    print("Database initialization: Starting...")
    init_db()
    print("Database initialization: OK")
except Exception as e:
    print(f"Database initialization: FAILED - {e}")
