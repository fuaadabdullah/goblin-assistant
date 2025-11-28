#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, "/Users/fuaadabdullah/ForgeMonorepo/goblin-assistant/api")

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Import the Flask app and functions
from app import app, init_db, get_api_keys_status


# Test the API key status function directly
def test_api_status():
    print("Testing API key status endpoint...")

    try:
        with app.app_context():
            # Initialize database
            init_db()

            # Call the status function directly
            from flask import jsonify

            result = get_api_keys_status()
            data = result.get_json()

            print("API Key Status Results:")
            for provider, status in data.items():
                configured = "✓" if status.get("configured") else "✗"
                enabled = "✓" if status.get("enabled") else "✗"
                models = len(status.get("models", []))
                print(
                    f"  {provider}: configured={configured}, enabled={enabled}, models={models}"
                )

            # Summary
            total_providers = len(data)
            configured_providers = sum(1 for s in data.values() if s.get("configured"))
            enabled_providers = sum(1 for s in data.values() if s.get("enabled"))

            print(f"\nSummary:")
            print(f"  Total providers: {total_providers}")
            print(f"  Configured: {configured_providers}")
            print(f"  Enabled: {enabled_providers}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_api_status()
