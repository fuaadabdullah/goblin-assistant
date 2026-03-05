#!/usr/bin/env python3
"""
Seed default settings data for goblin-assistant.
"""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from database import SessionLocal, create_tables
from services.settings import SettingsService


def seed_default_settings():
    """Seed default provider and model configurations"""
    # Create tables first
    print("🔧 Creating database tables...")
    create_tables()
    print("✅ Tables created successfully!")

    db = SessionLocal()
    try:
        service = SettingsService(db)

        # Seed default providers
        providers_data = [
            {
                "name": "openai",
                "display_name": "OpenAI",
                "capabilities": ["chat", "embedding"],
                "default_model": "gpt-4",
                "metadata": {"base_url": "https://api.openai.com/v1"},
            },
            {
                "name": "anthropic",
                "display_name": "Anthropic",
                "capabilities": ["chat"],
                "default_model": "claude-3-sonnet",
                "metadata": {"base_url": "https://api.anthropic.com"},
            },
            {
                "name": "groq",
                "display_name": "Groq",
                "capabilities": ["chat"],
                "default_model": "llama2-70b-4096",
                "metadata": {"base_url": "https://api.groq.com/openai/v1"},
            },
        ]

        for provider_data in providers_data:
            try:
                service.update_provider(provider_data["name"], provider_data)
                print(f"✅ Seeded provider: {provider_data['name']}")
            except Exception as e:
                print(f"⚠️  Failed to seed provider {provider_data['name']}: {e}")

        # Seed default models
        models_data = [
            {
                "model_name": "gpt-4",
                "provider_name": "openai",
                "params": {"temperature": 0.7, "max_tokens": 4096, "model_id": "gpt-4"},
            },
            {
                "model_name": "claude-3-sonnet",
                "provider_name": "anthropic",
                "params": {
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "model_id": "claude-3-sonnet-20240229",
                },
            },
            {
                "model_name": "llama2-70b-4096",
                "provider_name": "groq",
                "params": {
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "model_id": "llama2-70b-4096",
                },
            },
        ]

        for model_data in models_data:
            try:
                service.update_model(model_data["model_name"], model_data)
                print(f"✅ Seeded model: {model_data['model_name']}")
            except Exception as e:
                print(f"⚠️  Failed to seed model {model_data['model_name']}: {e}")

        print("🎉 Default settings seeded successfully!")

    except Exception as e:
        print(f"❌ Error seeding settings: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed_default_settings()
