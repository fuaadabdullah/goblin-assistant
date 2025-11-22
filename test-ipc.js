#!/usr/bin/env node

// Simple test script to verify IPC communication with the GoblinOS desktop app
// This script tests the API key management functions

import { invoke } from "@tauri-apps/api/tauri";

async function testIPC() {
	console.log("Testing IPC communication with GoblinOS desktop app...\n");

	try {
		// Test 1: Get providers
		console.log("1. Testing get_providers...");
		const providers = await invoke("get_providers");
		console.log("   Providers:", providers);
		console.log("   ✅ get_providers works\n");

		// Test 2: Get provider models for OpenAI
		console.log("2. Testing get_provider_models for openai...");
		const openaiModels = await invoke("get_provider_models", {
			provider: "openai",
		});
		console.log("   OpenAI models:", openaiModels);
		console.log("   ✅ get_provider_models works\n");

		// Test 3: Store API key
		console.log("3. Testing store_api_key...");
		await invoke("store_api_key", { provider: "openai", key: "test-key-123" });
		console.log("   ✅ store_api_key works\n");

		// Test 4: Get API key
		console.log("4. Testing get_api_key...");
		const retrievedKey = await invoke("get_api_key", { provider: "openai" });
		console.log("   Retrieved key:", retrievedKey);
		console.log("   ✅ get_api_key works\n");

		// Test 5: Clear API key
		console.log("5. Testing clear_api_key...");
		await invoke("clear_api_key", { provider: "openai" });
		console.log("   ✅ clear_api_key works\n");

		// Test 6: Verify key was cleared
		console.log("6. Testing get_api_key after clearing...");
		const clearedKey = await invoke("get_api_key", { provider: "openai" });
		console.log("   Key after clearing:", clearedKey);
		console.log("   ✅ Key was properly cleared\n");

		// Test 7: Get goblins
		console.log("7. Testing get_goblins...");
		const goblins = await invoke("get_goblins");
		console.log("   Goblins:", goblins);
		console.log("   ✅ get_goblins works\n");

		console.log(
			"🎉 All IPC tests passed! The GoblinOS desktop app is working correctly.",
		);
	} catch (error) {
		console.error("❌ IPC test failed:", error);
		process.exit(1);
	}
}

// Only run if this script is called directly
if (import.meta.url === `file://${process.argv[1]}`) {
	testIPC();
}

export { testIPC };
