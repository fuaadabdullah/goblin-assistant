import { expect, test } from "@playwright/test";

test("should load the main page", async ({ page }) => {
	await page.goto("/");
	await expect(page.locator("body")).toBeVisible();
});

test("should display provider selector", async ({ page }) => {
	await page.goto("/");

	// Wait for the app to load and providers to be fetched
	await page.waitForTimeout(2000);

	// Check if provider selector is visible
	const providerSelector = page.locator('[data-testid="provider-selector"], select, .provider-selector').first();
	await expect(providerSelector).toBeVisible();
});

test("should display cost panel", async ({ page }) => {
	await page.goto("/");

	// Wait for the app to load
	await page.waitForTimeout(2000);

	// Check if cost information is displayed
	const costPanel = page.locator('text=/cost|total|provider/i').first();
	await expect(costPanel).toBeVisible();
});

test("should display goblin demo section", async ({ page }) => {
	await page.goto("/");

	// Wait for the app to load
	await page.waitForTimeout(2000);

	// Check if goblin demo section is visible
	const goblinDemo = page.locator('text=/goblin|demo|execute/i').first();
	await expect(goblinDemo).toBeVisible();
});

test("provider selector should update model selector", async ({ page }) => {
	await page.goto("/");

	// Wait for the app to load and providers to be fetched
	await page.waitForTimeout(2000);

	// Locate the provider selector dropdown
	const providerSelector = page.locator('#provider-select');
	await expect(providerSelector).toBeVisible();

	// First select "anthropic" to ensure a change occurs
	await providerSelector.selectOption("anthropic");
	await page.waitForTimeout(1000);

	// Then select "openai" to trigger the model update
	await providerSelector.selectOption("openai");

	// Wait for model selector to update
	await page.waitForTimeout(1000);

	// Check if model selector is now visible and contains OpenAI models
	const modelSelector = page.locator('#model-select');
	await expect(modelSelector).toBeVisible();

	// Verify that the model selector contains OpenAI-specific models
	const modelOptions = modelSelector.locator('option');
	const optionTexts = await modelOptions.allTextContents();

	// Should contain OpenAI models like gpt-4, gpt-3.5-turbo, etc.
	expect(optionTexts).toContain("gpt-4");
	expect(optionTexts).toContain("gpt-3.5-turbo");
});

test("goblin demo should execute orchestration command", async ({ page }) => {
	await page.goto("/");

	// Wait for the app to load
	await page.waitForTimeout(2000);

	// Locate the orchestration input field
	const orchestrationInput = page.locator('#orch');
	await expect(orchestrationInput).toBeVisible();

	// Type a valid orchestration command into the orchestration input
	await orchestrationInput.fill("docs-writer: analyze this code");

	// Find and click the "Run" button
	const runButton = page.locator('button:has-text("Run")');
	await expect(runButton).toBeVisible();
	await expect(runButton).toBeEnabled();

	// Click the run button
	await runButton.click();

	// Wait for execution to start (button should become disabled)
	await expect(runButton).toHaveText("Running...");

	// Wait for execution to complete (button should become enabled again)
	await expect(runButton).toHaveText("Run");

	// Assert that some form of output is displayed in the StreamingView
	const streamingOutput = page.locator('.streaming-output');
	await expect(streamingOutput).toBeVisible();

	// Check that the output contains some text (indicating the command was processed)
	const outputText = await streamingOutput.textContent();
	expect(outputText?.trim()).not.toBe("");
});
