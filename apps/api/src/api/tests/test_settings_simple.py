#!/usr/bin/env python3
"""
Simple settings verification script.
Not part of automated pytest collection.
"""

import sys
import os
from pathlib import Path
import pytest

pytest.skip("Legacy script-style test; excluded from pytest suite.", allow_module_level=True)

# Set environment variables
os.environ["DATABASE_URL"] = "sqlite:///./goblin_assistant.db"
os.environ["SETTINGS_ENCRYPTION_KEY"] = "R-gey0ZNSPehux88bohbsUm9My8LAd09L2CbC_MRNo4="

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

def test_settings_service():
    """Test the settings service functionality"""
    from database import SessionLocal, create_tables
    from services.settings import SettingsService
    print("🧪 Testing Settings Service...")

    # Create tables
    create_tables()

    db = SessionLocal()
    try:
        service = SettingsService(db)

        # Test 1: Get all settings (should have seeded data)
        settings = service.get_all_settings()
        initial_providers_count = len(settings.get("providers", {}))
        print(f"✅ Initial providers count: {initial_providers_count}")

        # Test 2: Add a provider
        provider_data = {
            "name": "test_provider",
            "display_name": "Test Provider",
            "capabilities": ["chat"],
            "default_model": "test-model",
            "metadata": {"base_url": "https://test.com"},
        }
        service.update_provider("test_provider", provider_data)
        print("✅ Provider added successfully")

        # Test 3: Get provider
        provider = service.get_provider("test_provider")
        assert provider.name == "test_provider"
        assert provider.display_name == "Test Provider"
        print("✅ Provider retrieved successfully")

        # Test 4: Update provider
        updated_data = provider_data.copy()
        updated_data["display_name"] = "Updated Test Provider"
        service.update_provider("test_provider", updated_data)
        provider = service.get_provider("test_provider")
        assert provider.display_name == "Updated Test Provider"
        print("✅ Provider updated successfully")

        # Test 5: Add credential
        service.set_provider_credential("test_provider", "api_key", "test_key_123")
        print("✅ Credential set successfully")

        # Test 6: Get credential
        credential = service.get_provider_credential("test_provider", "api_key")
        assert credential == "test_key_123"
        print("✅ Credential retrieved successfully")

        # Test 7: Add model
        model_data = {
            "model_name": "test-model",
            "provider_name": "test_provider",
            "params": {"temperature": 0.5, "max_tokens": 1000},
        }
        service.update_model("test-model", model_data)
        print("✅ Model added successfully")

        # Test 8: Get model
        model = service.get_model("test-model")
        assert model.name == "test-model"
        assert model.params["temperature"] == 0.5
        print("✅ Model retrieved successfully")

        # Test 9: Verify test provider appears in all settings
        settings = service.get_all_settings()
        assert "test_provider" in settings.get("providers", {})
        test_provider_data = settings["providers"]["test_provider"]
        assert test_provider_data["display_name"] == "Updated Test Provider"
        print("✅ Test provider found in settings with updated name")

        print("🎉 All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()

    return True


if __name__ == "__main__":
    success = test_settings_service()
    sys.exit(0 if success else 1)
