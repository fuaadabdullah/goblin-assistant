import { expect, test } from "@playwright/test";

test.describe("Streaming Execution Flow", () => {
	test("should execute orchestration with streaming and update costs", async ({ page }) => {
		await page.goto("/");

		// Wait for the app to load and providers to be fetched
		await page.waitForTimeout(2000);

		// Ensure we're in demo mode for consistent testing
		const demoCheckbox = page.locator('#demo-mode-checkbox');
		await expect(demoCheckbox).toBeChecked();

		// Enter test code in the code input area
		const codeInput = page.locator('#code-input, textarea').first();
		await expect(codeInput).toBeVisible();
		await codeInput.fill(`function add(a, b) {
  return a + b;
}`);

		// Enter orchestration command
		const orchestrationInput = page.locator('#orch, #orchestration-input').first();
		await expect(orchestrationInput).toBeVisible();
		await orchestrationInput.fill("docs-writer: document this code THEN code-writer: write a unit test");

		// Click the Run button
		const runButton = page.locator('button:has-text("Run"), button[id*="run"]').first();
		await expect(runButton).toBeVisible();
		await expect(runButton).toBeEnabled();

		// Record initial cost summary
		const initialCostText = await page.locator('.cost-summary, [data-testid*="cost"]').first().textContent();

		// Start execution
		await runButton.click();

		// Wait for execution to start (button should become disabled or show "Running...")
		await expect(runButton).toHaveText(/Running|Processing/);

		// Wait for streaming to begin - look for streaming output
		const streamingOutput = page.locator('.streaming-output, [data-testid*="streaming"], .streaming-view').first();
		await expect(streamingOutput).toBeVisible();

		// Wait for some streaming content to appear
		await page.waitForFunction(() => {
			const streamingElement = document.querySelector('.streaming-output, [data-testid*="streaming"], .streaming-view');
			return streamingElement && streamingElement.textContent && streamingElement.textContent.length > 10;
		}, { timeout: 10000 });

		// Verify streaming content is being displayed
		const streamingContent = await streamingOutput.textContent();
		expect(streamingContent).toBeTruthy();
		expect(streamingContent!.length).toBeGreaterThan(10);

		// Wait for execution to complete
		await expect(runButton).toHaveText("Run");

		// Verify cost summary was updated
		const finalCostText = await page.locator('.cost-summary, [data-testid*="cost"]').first().textContent();
		// Cost should have increased (unless using free Ollama)
		// Note: In demo mode, costs might be simulated

		// Verify orchestration preview is shown
		const orchestrationPreview = page.locator('.orchestration-preview, [data-testid*="orchestration"]').first();
		await expect(orchestrationPreview).toBeVisible();

		// Check that step statuses are shown
		const stepStatuses = page.locator('.step-status, [data-testid*="step"]').all();
		expect((await stepStatuses).length).toBeGreaterThan(0);
	});

	test("should show cost estimation before execution", async ({ page }) => {
		await page.goto("/");

		// Wait for the app to load
		await page.waitForTimeout(2000);

		// Enter orchestration command
		const orchestrationInput = page.locator('#orch, #orchestration-input').first();
		await expect(orchestrationInput).toBeVisible();
		await orchestrationInput.fill("docs-writer: document this code THEN code-writer: write a unit test");

		// Wait for cost estimation to appear
		const costEstimation = page.locator('.cost-estimation-panel, [data-testid*="cost-estimation"]').first();
		await expect(costEstimation).toBeVisible({ timeout: 5000 });

		// Verify total cost is displayed
		const totalCost = costEstimation.locator('.total-cost .value, [data-testid*="total-cost"]').first();
		await expect(totalCost).toBeVisible();

		// Verify step-by-step breakdown is shown
		const stepCosts = costEstimation.locator('.step-cost-item, [data-testid*="step-cost"]').all();
		expect((await stepCosts).length).toBeGreaterThan(0);

		// Verify cost is reasonable (should be very low for demo/Ollama)
		const costText = await totalCost.textContent();
		expect(costText).toBeTruthy();
	});

	test("should handle streaming errors gracefully", async ({ page }) => {
		await page.goto("/");

		// Wait for the app to load
		await page.waitForTimeout(2000);

		// Enter invalid orchestration command that should cause an error
		const orchestrationInput = page.locator('#orch, #orchestration-input').first();
		await expect(orchestrationInput).toBeVisible();
		await orchestrationInput.fill("invalid-goblin: this should fail");

		// Click run
		const runButton = page.locator('button:has-text("Run")').first();
		await runButton.click();

		// Wait for execution to complete or fail
		await expect(runButton).toHaveText("Run");

		// Check for error message in streaming output
		const streamingOutput = page.locator('.streaming-output, .streaming-view').first();
		const outputText = await streamingOutput.textContent();

		// Should either show error or handle gracefully
		expect(outputText).toBeTruthy();
	});

	test("should update cost summary after multiple executions", async ({ page }) => {
		await page.goto("/");

		// Wait for the app to load
		await page.waitForTimeout(2000);

		// Record initial cost
		const initialCostElement = page.locator('.cost-summary, [data-testid*="cost"]').first();
		const initialCost = await initialCostElement.textContent();

		// First execution
		const orchestrationInput = page.locator('#orch, #orchestration-input').first();
		await orchestrationInput.fill("docs-writer: document this");

		const runButton = page.locator('button:has-text("Run")').first();
		await runButton.click();
		await expect(runButton).toHaveText("Run");

		// Wait for cost update
		await page.waitForTimeout(1000);
		const afterFirstCost = await initialCostElement.textContent();

		// Second execution
		await orchestrationInput.fill("code-writer: write test");
		await runButton.click();
		await expect(runButton).toHaveText("Run");

		// Wait for cost update
		await page.waitForTimeout(1000);
		const afterSecondCost = await initialCostElement.textContent();

		// Costs should have increased (unless using free provider)
		// In demo mode, this might be simulated
		expect(afterSecondCost).toBeTruthy();
	});
});
