#!/usr/bin/env python3
"""
Test script for the streaming functionality
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from fastapi.testclient import TestClient


def test_health():
    client = TestClient(app)
    response = client.get("/api/health")
    print(f"Health check: {response.status_code} - {response.json()}")


def test_providers():
    client = TestClient(app)
    response = client.get("/providers")
    print(f"Providers: {response.status_code} - {response.json()}")


if __name__ == "__main__":
    print("Testing FastAPI endpoints...")
    test_health()
    test_providers()
    print("Tests completed!")
