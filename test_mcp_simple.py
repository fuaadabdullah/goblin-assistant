#!/usr/bin/env python3
"""
Simple test script for MCP components without full server.
"""

import sys
import os

sys.path.append("/usr/local/lib/python3.11/site-packages")
sys.path.append("./api/fastapi")

try:
    from mcp_models import MCPRequest, get_database_url
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import json

    print("✅ MCP imports successful")

    # Test database connection
    engine = create_engine(get_database_url())
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    print("✅ Database connection successful")

    # Test creating a request
    db = SessionLocal()
    test_request = MCPRequest(
        user_hash="test123", status="pending", task_type="chat", priority=50
    )

    db.add(test_request)
    db.commit()
    db.refresh(test_request)

    print(f"✅ Created test request with ID: {test_request.id}")

    # Clean up
    db.delete(test_request)
    db.commit()
    db.close()

    print("✅ MCP components working correctly!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
