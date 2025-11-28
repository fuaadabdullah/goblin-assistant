#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, "/Users/fuaadabdullah/ForgeMonorepo/goblin-assistant/api")

try:
    print("Testing imports...")
    from dotenv import load_dotenv

    load_dotenv()
    print("✓ dotenv loaded")

    from flask import Flask

    print("✓ Flask imported")

    from flask_sqlalchemy import SQLAlchemy

    print("✓ SQLAlchemy imported")

    print("Testing app import...")
    from app import app, init_db

    print("✓ App imported successfully")

    print("Testing database initialization...")
    init_db()
    print("✓ Database initialized")

    print("All tests passed! Starting server...")
    app.run(host="0.0.0.0", port=5000, debug=True)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
