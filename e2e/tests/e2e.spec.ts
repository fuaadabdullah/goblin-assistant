import { test, expect } from "@playwright/test";

test("should run e2e with mocked network", async ({ page }) => {
	// Mock data for providers and models
	const MOCK_PROVIDERS = ["openai", "gemini"];
	const MOCK_MODELS = {
	openai: ["gpt-4", "gpt-3.5-turbo"],
		gemini: ["gemini-pro", "gemini-ultra"],
	};

	// Mock the /providers endpoint
	await page.route("**/providers", (route) => {
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify(MOCK_PROVIDERS),
		});
	});

	// Mock the /models/{provider} endpoint
	await page.route("**/models/*", (route) => {
		const url = new URL(route.request().url());
		const provider = url.pathname.split("/").pop();
		const models = MOCK_MODELS[provider] || [];
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify(models),
		});
	});

	// Mock the /execute endpoint
	await page.route("**/execute", (route) => {
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify({ taskId: "mock-task-id" }),
		});
	});

	// Mock the /stream endpoint
	await page.route("**/stream**", (route) => {
		const headers = {
			"Content-Type": "text/event-stream",
			"Cache-Control": "no-cache",
			Connection: "keep-alive",
		};
		route.fulfill({
			status: 200,
			headers,
			body: `event: chunk\ndata: {"taskId":"mock-task-id","chunk":"Analyzing code...","token_count":2,"cost_delta":0.000002,"provider":"openai","model":"gpt-4","is_code":false}\n\n` +
				`event: chunk\ndata: {"taskId":"mock-task-id","chunk":"\\n## Function Documentation\\n","token_count":4,"cost_delta":0.000004,"provider":"openai","model":"gpt-4","is_code":false}\n\n` +
				`event: chunk\ndata: {"taskId":"mock-task-id","result":true,"cost":0.000006,"output":"Analyzing code...\\n## Function Documentation\\n","total_tokens":6}\n\n`,
		});
	});

	await page.goto("/");

	// The provider selector should be visible
	const providerSelector = page.locator("#provider-select");
	await expect(providerSelector).toBeVisible();

	// It should contain the mocked providers
	const options = providerSelector.locator("option");
	expect(await options.allTextContents()).toContain("openai");
	expect(await options.allTextContents()).toContain("gemini");

	// Select "openai" provider
	await providerSelector.selectOption("openai");

	// The model selector should be visible and contain OpenAI models
	const modelSelector = page.locator("#model-select");
	await expect(modelSelector).toBeVisible();
	const modelOptions = modelSelector.locator("option");
	expect(await modelOptions.allTextContents()).toEqual(MOCK_MODELS.openai);

	// Locate the orchestration input field
	const orchestrationInput = page.locator("#orch");
	await expect(orchestrationInput).toBeVisible();

	// Type a valid orchestration command
	await orchestrationInput.fill("docs-writer: analyze this code");

	// Find and click the "Run" button
	const runButton = page.locator('button:has-text("Run")');
	await expect(runButton).toBeVisible();
	await expect(runButton).toBeEnabled();

	// Click the run button
	await runButton.click();

	// Wait for execution to start
	await expect(runButton).toHaveText("Running...");

	// Wait for execution to complete
	await expect(runButton).toHaveText("Run");

	// Assert that the mocked output is displayed
	const streamingOutput = page.locator(".streaming-output");
	await expect(streamingOutput).toBeVisible();
	const outputText = await streamingOutput.textContent();
	expect(outputText).toContain("Analyzing code...");
	expect(outputText).toContain("## Function Documentation");
});