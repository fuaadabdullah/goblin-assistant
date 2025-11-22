#!/usr/bin/env node

// Comprehensive test script for GoblinOS desktop API key functionality
// This script tests all IPC commands to ensure they work correctly

import { invoke } from "@tauri-apps/api/core";

async function testAPIKeyFunctionality() {
	console.log("🧪 Testing GoblinOS Desktop API Key Functionality\n");

	const results = {
		passed: 0,
		failed: 0,
		tests: [],
	};

	const logResult = (testName, success, message = "") => {
		const status = success ? "✅ PASS" : "❌ FAIL";
		console.log(`${status} ${testName}${message ? ": " + message : ""}`);
		results.tests.push({ testName, success, message });
		if (success) results.passed++;
		else results.failed++;
	};

	try {
		// Test 1: Get providers
		console.log("1. Testing get_providers...");
		try {
			const providers = await invoke("get_providers");
			const expectedProviders = [
				"openai",
				"anthropic",
				"gemini",
				"ollama",
				"deepseek",
			];
			const hasExpectedProviders = expectedProviders.every((p) =>
				providers.includes(p),
			);
			logResult(
				"get_providers",
				hasExpectedProviders,
				`Got: ${providers.join(", ")}`,
			);
		} catch (error) {
			logResult("get_providers", false, error.message);
		}

		// Test 2: Get provider models for OpenAI
		console.log("2. Testing get_provider_models for openai...");
		try {
			const models = await invoke("get_provider_models", {
				provider: "openai",
			});
			const expectedModels = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"];
			const hasExpectedModels = expectedModels.every((m) => models.includes(m));
			logResult(
				"get_provider_models (openai)",
				hasExpectedModels,
				`Got: ${models.join(", ")}`,
			);
		} catch (error) {
			logResult("get_provider_models (openai)", false, error.message);
		}

		// Test 3: Store API key
		console.log("3. Testing store_api_key...");
		try {
			const testKey = "sk-test-1234567890abcdef";
			await invoke("store_api_key", { provider: "openai", key: testKey });
			logResult("store_api_key", true, "Key stored successfully");
		} catch (error) {
			logResult("store_api_key", false, error.message);
		}

		// Test 4: Get API key
		console.log("4. Testing get_api_key...");
		try {
			const retrievedKey = await invoke("get_api_key", { provider: "openai" });
			const expectedKey = "sk-test-1234567890abcdef";
			const keyMatches = retrievedKey === expectedKey;
			logResult(
				"get_api_key",
				keyMatches,
				`Retrieved: ${retrievedKey ? "Present" : "Not found"}`,
			);
		} catch (error) {
			logResult("get_api_key", false, error.message);
		}

		// Test 5: Store different provider key
		console.log("5. Testing store_api_key for anthropic...");
		try {
			const testKey = "sk-ant-test-abcdef123456";
			await invoke("store_api_key", { provider: "anthropic", key: testKey });
			logResult(
				"store_api_key (anthropic)",
				true,
				"Anthropic key stored successfully",
			);
		} catch (error) {
			logResult("store_api_key (anthropic)", false, error.message);
		}

		// Test 6: Get anthropic key
		console.log("6. Testing get_api_key for anthropic...");
		try {
			const retrievedKey = await invoke("get_api_key", {
				provider: "anthropic",
			});
			const expectedKey = "sk-ant-test-abcdef123456";
			const keyMatches = retrievedKey === expectedKey;
			logResult(
				"get_api_key (anthropic)",
				keyMatches,
				`Retrieved: ${retrievedKey ? "Present" : "Not found"}`,
			);
		} catch (error) {
			logResult("get_api_key (anthropic)", false, error.message);
		}

		// Test 7: Clear OpenAI key
		console.log("7. Testing clear_api_key for openai...");
		try {
			await invoke("clear_api_key", { provider: "openai" });
			logResult(
				"clear_api_key (openai)",
				true,
				"OpenAI key cleared successfully",
			);
		} catch (error) {
			logResult("clear_api_key (openai)", false, error.message);
		}

		// Test 8: Verify OpenAI key was cleared
		console.log("8. Testing get_api_key after clearing openai...");
		try {
			const retrievedKey = await invoke("get_api_key", { provider: "openai" });
			const keyCleared = retrievedKey === null;
			logResult(
				"get_api_key (openai cleared)",
				keyCleared,
				`Key status: ${retrievedKey ? "Still present" : "Cleared"}`,
			);
		} catch (error) {
			logResult("get_api_key (openai cleared)", false, error.message);
		}

		// Test 9: Verify Anthropic key still exists
		console.log("9. Testing get_api_key for anthropic (should still exist)...");
		try {
			const retrievedKey = await invoke("get_api_key", {
				provider: "anthropic",
			});
			const keyExists = retrievedKey !== null;
			logResult(
				"get_api_key (anthropic still exists)",
				keyExists,
				`Key status: ${retrievedKey ? "Present" : "Missing"}`,
			);
		} catch (error) {
			logResult("get_api_key (anthropic still exists)", false, error.message);
		}

		// Test 10: Test set_provider_api_key (alias)
		console.log("10. Testing set_provider_api_key...");
		try {
			const testKey = "sk-set-test-xyz789";
			await invoke("set_provider_api_key", {
				provider: "gemini",
				key: testKey,
			});
			const retrievedKey = await invoke("get_api_key", { provider: "gemini" });
			const keyMatches = retrievedKey === testKey;
			logResult(
				"set_provider_api_key",
				keyMatches,
				"Set and retrieved successfully",
			);
		} catch (error) {
			logResult("set_provider_api_key", false, error.message);
		}

		// Test 11: Test invalid provider
		console.log("11. Testing get_provider_models for invalid provider...");
		try {
			const models = await invoke("get_provider_models", {
				provider: "invalid_provider",
			});
			const isEmptyArray = Array.isArray(models) && models.length === 0;
			logResult(
				"get_provider_models (invalid)",
				isEmptyArray,
				`Got: ${models.join(", ")}`,
			);
		} catch (error) {
			logResult("get_provider_models (invalid)", false, error.message);
		}

		// Test 12: Test get_goblins (basic functionality)
		console.log("12. Testing get_goblins...");
		try {
			const goblins = await invoke("get_goblins");
			const isArray = Array.isArray(goblins);
			logResult("get_goblins", isArray, `Got ${goblins.length} goblins`);
		} catch (error) {
			logResult("get_goblins", false, error.message);
		}

		// Test 13: Test get_cost_summary
		console.log("13. Testing get_cost_summary...");
		try {
			const costSummary = await invoke("get_cost_summary");
			const hasExpectedStructure =
				typeof costSummary === "object" &&
				"total_cost" in costSummary &&
				"cost_by_provider" in costSummary &&
				"cost_by_model" in costSummary;
			logResult(
				"get_cost_summary",
				hasExpectedStructure,
				`Structure: ${Object.keys(costSummary).join(", ")}`,
			);
		} catch (error) {
			logResult("get_cost_summary", false, error.message);
		}
	} catch (error) {
		console.error("💥 Test suite failed with error:", error);
		results.failed++;
	}

	// Summary
	console.log("\n📊 Test Results Summary:");
	console.log(`   ✅ Passed: ${results.passed}`);
	console.log(`   ❌ Failed: ${results.failed}`);
	console.log(
		`   📈 Success Rate: ${((results.passed / (results.passed + results.failed)) * 100).toFixed(1)}%`,
	);

	if (results.failed === 0) {
		console.log(
			"\n🎉 All API key functionality tests passed! The GoblinOS desktop app is working correctly.",
		);
	} else {
		console.log("\n⚠️  Some tests failed. Check the output above for details.");
	}

	return results;
}

// Only run if this script is called directly
if (import.meta.url === `file://${process.argv[1]}`) {
	testAPIKeyFunctionality();
}

export { testAPIKeyFunctionality };
