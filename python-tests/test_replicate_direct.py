#!/usr/bin/env python3
"""
Test Replicate API directly to understand the correct format.
"""

import os
from dotenv import load_dotenv
import replicate

# Load environment
load_dotenv()


def test_replicate_direct():
    print("🔍 Testing Replicate API directly")
    print("=" * 40)

    api_key = os.getenv("REPLICATE_API_KEY")
    if not api_key:
        print("❌ No REPLICATE_API_KEY found")
        return

    print(f"🔑 API Key loaded: {api_key[:10]}...")

    try:
        # Initialize client
        client = replicate.Client(api_token=api_key)

        # Try a simple API call to check if key works
        print("🔍 Testing API key with a simple call...")
        models = client.models.list()
        model_list = list(models)
        print(f"✅ API key works! Found {len(model_list)} models")

        # Look for SDXL models
        sdxl_models = [
            m
            for m in model_list
            if "sdxl" in m.name.lower() or "stable-diffusion" in m.name.lower()
        ]
        print(f"🎨 Found {len(sdxl_models)} SDXL/stable diffusion models:")
        for i, model in enumerate(sdxl_models[:5]):  # Show first 5
            print(f"  {i + 1}. {model.owner}/{model.name}")
        print()

        # Try to run the first available SDXL model
        if sdxl_models:
            model = f"{sdxl_models[0].owner}/{sdxl_models[0].name}"
            print(f"🎨 Running model: {model}")
        else:
            print("❌ No SDXL models found, trying a different model...")
            model = f"{model_list[0].owner}/{model_list[0].name}"
            print(f"🎨 Running model: {model}")

        # This should work with Replicate client
        output = client.run(
            model,
            input={
                "prompt": "A beautiful sunset over mountains",
                "width": 512,
                "height": 512,
            },
        )

        print(f"✅ Success! Output: {output}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_replicate_direct()
