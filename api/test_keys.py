#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, "/Users/fuaadabdullah/ForgeMonorepo/goblin-assistant/api")

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Import the Flask app
from app import app, db, Provider, init_db


# Test the API key loading
def test_api_keys():
    print("Testing API key loading...")

    # Test environment variables
    api_keys = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
        "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY"),
        "SILICONFLOW_API_KEY": os.getenv("SILICONFLOW_API_KEY"),
        "MOONSHOT_API_KEY": os.getenv("MOONSHOT_API_KEY"),
        "FIREWORKS_API_KEY": os.getenv("FIREWORKS_API_KEY"),
        "ELEVENLABS_API_KEY": os.getenv("ELEVENLABS_API_KEY"),
        "DATADOG_API_KEY": os.getenv("DATADOG_API_KEY"),
        "NETLIFY_API_KEY": os.getenv("NETLIFY_API_KEY"),
    }

    print("\nEnvironment Variables Status:")
    for key, value in api_keys.items():
        has_value = bool(value and value.strip())
        masked_value = "***" + value[-4:] if has_value and len(value) > 4 else "NOT SET"
        print(f"  {key}: {'✓' if has_value else '✗'} {masked_value}")

    # Test database initialization
    print("\nTesting database initialization...")
    try:
        with app.app_context():
            init_db()  # Force re-initialization with API keys
            print("✓ Database initialization completed")

            # Check if providers exist
            providers = Provider.query.all()
            print(f"✓ Found {len(providers)} providers in database")
            for provider in providers:
                has_key = bool(provider.api_key and provider.api_key.strip())
                print(
                    f"    {provider.name}: {'✓' if has_key else '✗'} API key configured"
                )
    except Exception as e:
        print(f"✗ Database error: {e}")

    print("\nTest completed!")


if __name__ == "__main__":
    test_api_keys()
