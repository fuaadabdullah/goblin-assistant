#!/usr/bin/env python3
"""
Simple test script to verify API key configuration for Goblin Assistant
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir.parent / "src"))

# Try to import dotenv, fallback to manual loading
try:
    from dotenv import load_dotenv

    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

    def load_dotenv(file):
        """Manual dotenv loading fallback"""
        if Path(file).exists():
            with open(file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        key, _, value = line.partition("=")
                        if key and value:
                            os.environ[key.strip()] = value.strip()


def main():
    # Load environment variables
    load_dotenv(".env")

    print("🔍 Goblin Assistant API Key Verification")
    print("=" * 50)

    # Test key loading
    api_keys = {
        "ANTHROPIC_API_KEY": "sk-ant-api03-",
        "DEEPSEEK_API_KEY": "sk-",
        "GEMINI_API_KEY": "AIzaSy",
        "GROK_API_KEY": "xai-",
        "SILICONFLOW_API_KEY": "sk-",
        "MOONSHOT_API_KEY": "sk-",
        "FIREWORKS_API_KEY": "fw_",
        "ELEVENLABS_API_KEY": "sk_",
        "CLOUDFLARE_GLOBAL_API_KEY": "",
        "CLOUDFLARE_CAKEY_V10": "",
        "DASHSCOPE_API_KEY": "sk-",
    }

    configured = 0
    for key_name, expected_prefix in api_keys.items():
        value = os.getenv(key_name)
        if (
            value
            and value != f"your-{key_name.lower().replace('_api_key', '')}-key-here"
            and value != "..."
        ):
            if expected_prefix and value.startswith(expected_prefix):
                print(f"✅ {key_name}: Properly configured")
                configured += 1
            elif not expected_prefix:
                print(f"✅ {key_name}: Configured")
                configured += 1
            else:
                print(f"⚠️  {key_name}: Set but unexpected format")
        else:
            print(f"❌ {key_name}: Not configured")

    print("=" * 50)
    print(f"📊 Summary: {configured}/{len(api_keys)} API keys configured")
    print("🎯 All configured keys are accessible to the FastAPI backend!")


if __name__ == "__main__":
    main()
