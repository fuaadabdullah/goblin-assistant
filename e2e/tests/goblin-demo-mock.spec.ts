import { expect, test, Page } from "@playwright/test";

test.describe("Goblin Assistant Demo with Network Mocking", () => {
  // Helper function to set up all mocks
  async function setupMocks(page: Page) {
    // Mock the /providers endpoint (returns string[])
    await page.route("http://127.0.0.1:3001/providers", async (route) => {
      console.log('Intercepted /providers request');
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(["openai", "anthropic", "google"]),
      });
    });

    // Mock the /models/{provider} endpoint
    await page.route("http://127.0.0.1:3001/models/*", async (route) => {
      const url = route.request().url();
      const provider = url.split("/").pop();

      let models: string[] = [];
      switch (provider) {
        case "openai":
          models = ["gpt-4", "gpt-3.5-turbo"];
          break;
        case "anthropic":
          models = ["claude-3", "claude-2"];
          break;
        case "google":
          models = ["gemini-pro", "gemini-pro-vision"];
          break;
        default:
          models = [];
      }

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(models),
      });
    });

    // Mock the /parse endpoint for orchestration planning
    await page.route("http://127.0.0.1:3001/parse", async (route) => {
      const requestData = route.request().postDataJSON();

      const mockPlan = {
        steps: [
          { id: "step-1", goblin: "docs-writer", task: "document this code" },
          { id: "step-2", goblin: "code-writer", task: "write a unit test" },
        ],
        total_batches: 1,
        max_parallel: 1,
        estimated_cost: 0.0025,
      };

      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mockPlan) });
    });

    // Mock the /execute endpoint to return a task ID for streaming
    await page.route("http://127.0.0.1:3001/execute", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ taskId: "mock-task-1" }) });
    });

    // Mock the /stream endpoint for streaming execution
    await page.route("http://127.0.0.1:3001/stream", async (route) => {
      // Simulate streaming response with Server-Sent Events
      const mockStreamData = [
        "data: {\"step_id\": \"step-1\", \"chunk\": \"Starting documentation...\", \"tokens\": 50, \"cost\": 0.0001}\n\n",
        "data: {\"step_id\": \"step-1\", \"chunk\": \"Analyzing function structure...\", \"tokens\": 75, \"cost\": 0.0002}\n\n",
        "data: {\"step_id\": \"step-1\", \"chunk\": \"Documentation complete.\", \"tokens\": 25, \"cost\": 0.00005}\n\n",
        "data: {\"step_id\": \"step-2\", \"chunk\": \"Writing unit test...\", \"tokens\": 100, \"cost\": 0.0003}\n\n",
        "data: {\"step_id\": \"step-2\", \"chunk\": \"Test completed successfully.\", \"tokens\": 50, \"cost\": 0.00015}\n\n"
      ];

      // Send streaming data with delays to simulate real streaming
      let response = "data: {\"type\": \"start\"}\n\n";
      for (const chunk of mockStreamData) {
        response += chunk;
        await new Promise(resolve => setTimeout(resolve, 100)); // Small delay between chunks
      }
      response += "data: {\"type\": \"end\"}\n\n";

      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: response
      });
    });
  }

  test("should load the app and display provider selector", async ({ page }) => {
    await setupMocks(page);
    await page.goto("/");

    // Check that the app container is visible
    await expect(page.getByTestId("app-container")).toBeVisible();

    // Check that the provider selector is present
    await expect(page.getByTestId("provider-selector")).toBeVisible();
    await expect(page.getByTestId("provider-label")).toHaveText("Provider:");
  });

  test("should load providers and allow selection", async ({ page }) => {
    // --- debug logs --------------------------
    page.on('console', m => console.log('PAGE LOG>', m.type(), m.text()));
    page.on('request', r => console.log('REQ>', r.method(), r.url()));
    page.on('response', r => console.log('RES>', r.status(), r.url()));
    page.on('requestfailed', r => console.log('REQ FAILED>', r.url(), r.failure()?.errorText));

    // --- mock BEFORE navigation ----
    await setupMocks(page);

    // ---- navigate ----------------------------
    await page.goto("/?demo=false", { waitUntil: 'networkidle' });

    // --- wait for the mocked network calls ----
    await page.waitForResponse(resp => /\/providers/.test(resp.url()), { timeout: 40000 });

    // --- wait for selector ----
    await page.waitForSelector('[data-testid="provider-select"]', { timeout: 30000 });

    // --- verify options actually present in DOM ---
    // Wait for the option element to be created (use value attribute match)
    await page.waitForSelector('select[data-testid="provider-select"] option[value="openai"]', { timeout: 30000 });

    // --- select by value (explicit) -----------
    await page.getByTestId('provider-select').selectOption({ value: 'openai' });

    // --- wait for models request + model option ---
    await page.waitForResponse(resp => /\/models/.test(resp.url()) && resp.status() === 200, { timeout: 30000 });
    await page.waitForSelector('select[data-testid="model-select"] option[value="gpt-4"]', { timeout: 30000 });

    // --- select model and assert UI shows selection ---
    await page.getByTestId('model-select').selectOption({ value: 'gpt-4' });

    // Check that model selector becomes available
    await expect(page.getByTestId("model-selector")).toBeVisible();
  });

  test("should load models for selected provider", async ({ page }) => {
    // --- debug logs --------------------------
    page.on('console', m => console.log('PAGE LOG>', m.type(), m.text()));
    page.on('request', r => console.log('REQ>', r.method(), r.url()));
    page.on('response', r => console.log('RES>', r.status(), r.url()));
    page.on('requestfailed', r => console.log('REQ FAILED>', r.url(), r.failure()?.errorText));

    // --- mock BEFORE navigation ----
    await setupMocks(page);

    // ---- navigate ----------------------------
    await page.goto("/?demo=false", { waitUntil: 'networkidle' });

    // --- wait for providers ----
    await page.waitForResponse(resp => /\/providers/.test(resp.url()), { timeout: 40000 });
    await page.waitForSelector('select[data-testid="provider-select"] option[value="openai"]', { timeout: 30000 });

    // Select provider
    await page.getByTestId("provider-select").selectOption({ value: "openai" });

    // Wait for models to load
    await page.waitForResponse(resp => /\/models/.test(resp.url()) && resp.status() === 200, { timeout: 30000 });
    await page.waitForSelector('select[data-testid="model-select"] option[value="gpt-4"]', { timeout: 30000 });

    // Check that OpenAI models are available
    await expect(page.getByTestId("model-option-gpt-4")).toBeVisible();
    await expect(page.getByTestId("model-option-gpt-3.5-turbo")).toBeVisible();

    // Select a model
    await page.getByTestId("model-select").selectOption({ value: "gpt-4" });
  });

  test("should display goblin demo interface", async ({ page }) => {
    // --- debug logs --------------------------
    page.on('console', m => console.log('PAGE LOG>', m.type(), m.text()));
    page.on('request', r => console.log('REQ>', r.method(), r.url()));
    page.on('response', r => console.log('RES>', r.status(), r.url()));
    page.on('requestfailed', r => console.log('REQ FAILED>', r.url(), r.failure()?.errorText));

    // --- mock BEFORE navigation ----
    await setupMocks(page);

    // ---- navigate ----------------------------
    await page.goto("/?demo=false", { waitUntil: 'networkidle' });

    // --- wait for providers ----
    await page.waitForResponse(resp => /\/providers/.test(resp.url()), { timeout: 40000 });
    await page.waitForSelector('select[data-testid="provider-select"] option[value="openai"]', { timeout: 30000 });

    // Select provider and model
    await page.getByTestId("provider-select").selectOption({ value: "openai" });
    await page.waitForResponse(resp => /\/models/.test(resp.url()) && resp.status() === 200, { timeout: 30000 });
    await page.waitForSelector('select[data-testid="model-select"] option[value="gpt-4"]', { timeout: 30000 });
    await page.getByTestId("model-select").selectOption({ value: "gpt-4" });

    // Check that goblin demo is visible
    await expect(page.getByTestId("goblin-demo")).toBeVisible();

    // Check input areas
    await expect(page.getByTestId("code-input")).toBeVisible();
    await expect(page.getByTestId("orchestration-input")).toBeVisible();
    await expect(page.getByTestId("template-select")).toBeVisible();

    // Check run button
    await expect(page.getByTestId("run-button")).toBeVisible();
    await expect(page.getByTestId("run-button")).toHaveText("Run Orchestration");
  });

  test("should execute orchestration and show results", async ({ page }) => {
    await setupMocks(page);
    await page.goto("/?demo=false");

    // --- disable demo mode AFTER navigation ---
    // Instead of clicking checkbox, directly set demo mode via JavaScript
    await page.evaluate(() => {
      // Find the React component and set demoMode to false
      const appContainer = document.querySelector('[data-testid="app-container"]');
      if (appContainer) {
        // Trigger a state change by dispatching a custom event or using React dev tools
        // For now, we'll simulate the checkbox change
        const checkbox = document.querySelector('[data-testid="demo-mode-checkbox"]') as HTMLInputElement;
        if (checkbox && checkbox.checked) {
          checkbox.checked = false;
          // Dispatch change event to trigger React onChange
          const changeEvent = new Event('change', { bubbles: true });
          checkbox.dispatchEvent(changeEvent);
        }
      }
    });

    // Wait a bit for the state change to take effect
    await page.waitForTimeout(1000);

    // Setup provider and model
    await page.getByTestId("provider-select").selectOption("openai");
    await page.getByTestId("model-select").selectOption("gpt-4");

    // Enter some code
    await page.getByTestId("code-input").fill("function add(a, b) { return a + b; }");

    // Click run button
    await page.getByTestId("run-button").click();

    // Wait for execution plan to appear
    await expect(page.getByTestId("execution-plan")).toBeVisible();
    await expect(page.getByTestId("execution-plan-title")).toHaveText("Plan Preview");

    // Check that steps are displayed
    await expect(page.getByTestId("execution-steps")).toBeVisible();
    await expect(page.getByTestId("execution-step-step-1")).toBeVisible();
    await expect(page.getByTestId("execution-step-step-2")).toBeVisible();

    // Check step details
    await expect(page.getByTestId("execution-step-goblin-step-1")).toHaveText("docs-writer");
    await expect(page.getByTestId("execution-step-task-step-1")).toContainText("document this code");

    // Check streaming view appears
    await expect(page.getByTestId("streaming-view")).toBeVisible();
    await expect(page.getByTestId("streaming-title")).toHaveText("Streaming Output");
  });

  test("should show step details when expanded", async ({ page }) => {
    await setupMocks(page);
    await page.goto("/?demo=false");

    // --- disable demo mode AFTER navigation ---
    // Instead of clicking checkbox, directly set demo mode via JavaScript
    await page.evaluate(() => {
      // Find the React component and set demoMode to false
      const appContainer = document.querySelector('[data-testid="app-container"]');
      if (appContainer) {
        // Trigger a state change by dispatching a custom event or using React dev tools
        // For now, we'll simulate the checkbox change
        const checkbox = document.querySelector('[data-testid="demo-mode-checkbox"]') as HTMLInputElement;
        if (checkbox && checkbox.checked) {
          checkbox.checked = false;
          // Dispatch change event to trigger React onChange
          const changeEvent = new Event('change', { bubbles: true });
          checkbox.dispatchEvent(changeEvent);
        }
      }
    });

    // Wait a bit for the state change to take effect
    await page.waitForTimeout(1000);

    // Setup and run orchestration
    await page.getByTestId("provider-select").selectOption("openai");
    await page.getByTestId("model-select").selectOption("gpt-4");
    await page.getByTestId("code-input").fill("function add(a, b) { return a + b; }");
    await page.getByTestId("run-button").click();

    // Wait for plan and click on first step to expand
    await expect(page.getByTestId("execution-step-step-1")).toBeVisible();
    await page.getByTestId("execution-step-step-1").click();

    // Check that step details are shown
    await expect(page.getByTestId("step-details-step-1")).toBeVisible();
    await expect(page.getByTestId("step-id-step-1")).toContainText("Step ID: step-1");
    await expect(page.getByTestId("step-status-step-1")).toContainText("Status:");
  });

  test("should handle template selection", async ({ page }) => {
    await setupMocks(page);
    await page.goto("/?demo=false");

    // --- disable demo mode AFTER navigation ---
    // Instead of clicking checkbox, directly set demo mode via JavaScript
    await page.evaluate(() => {
      // Find the React component and set demoMode to false
      const appContainer = document.querySelector('[data-testid="app-container"]');
      if (appContainer) {
        // Trigger a state change by dispatching a custom event or using React dev tools
        // For now, we'll simulate the checkbox change
        const checkbox = document.querySelector('[data-testid="demo-mode-checkbox"]') as HTMLInputElement;
        if (checkbox && checkbox.checked) {
          checkbox.checked = false;
          // Dispatch change event to trigger React onChange
          const changeEvent = new Event('change', { bubbles: true });
          checkbox.dispatchEvent(changeEvent);
        }
      }
    });

    // Wait a bit for the state change to take effect
    await page.waitForTimeout(1000);

    // Setup provider and model
    await page.getByTestId("provider-select").selectOption("openai");
    await page.getByTestId("model-select").selectOption("gpt-4");

    // Check template selector
    await expect(page.getByTestId("template-select")).toBeVisible();

    // Select "Analyze & Optimize" template
    await page.getByTestId("template-select").selectOption("Analyze & Optimize");

    // Check that orchestration input is updated
    const orchestrationValue = await page.getByTestId("orchestration-input").inputValue();
    expect(orchestrationValue).toContain("analyze this code for issues");
  });

  test("should show streaming indicator during execution", async ({ page }) => {
    await setupMocks(page);
    await page.goto("/?demo=false");

    // --- disable demo mode AFTER navigation ---
    // Instead of clicking checkbox, directly set demo mode via JavaScript
    await page.evaluate(() => {
      // Find the React component and set demoMode to false
      const appContainer = document.querySelector('[data-testid="app-container"]');
      if (appContainer) {
        // Trigger a state change by dispatching a custom event or using React dev tools
        // For now, we'll simulate the checkbox change
        const checkbox = document.querySelector('[data-testid="demo-mode-checkbox"]') as HTMLInputElement;
        if (checkbox && checkbox.checked) {
          checkbox.checked = false;
          // Dispatch change event to trigger React onChange
          const changeEvent = new Event('change', { bubbles: true });
          checkbox.dispatchEvent(changeEvent);
        }
      }
    });

    // Wait a bit for the state change to take effect
    await page.waitForTimeout(1000);

    // Setup and run orchestration
    await page.getByTestId("provider-select").selectOption("openai");
    await page.getByTestId("model-select").selectOption("gpt-4");
    await page.getByTestId("code-input").fill("function add(a, b) { return a + b; }");
    await page.getByTestId("run-button").click();

    // Check that streaming indicator appears
    await expect(page.getByTestId("streaming-indicator")).toBeVisible();
    await expect(page.getByTestId("streaming-indicator")).toHaveText("● Streaming");

    // Wait for streaming to complete (indicator should disappear)
    await page.waitForTimeout(2000);
    // Note: In a real test, you'd wait for the streaming to actually complete
  });

  test("should override runtime client and execute orchestration", async ({ page }) => {
    await setupMocks(page);
    await page.goto("/?demo=false");

    // Override the runtime client to use FastAPI client instead of Mock client
    await page.evaluate(() => {
      // Import the FastAPI client and override the runtimeClient
      import('/src/api/tauri-client.ts').then(module => {
        window.runtimeClient = module.runtimeClientFast;
        // Trigger a re-render or re-fetch
        const event = new CustomEvent('runtimeClientChanged');
        window.dispatchEvent(event);
      });
    });

    // Wait a bit for the client override to take effect
    await page.waitForTimeout(1000);

    // --- disable demo mode AFTER navigation ---
    // Instead of clicking checkbox, directly set demo mode via JavaScript
    await page.evaluate(() => {
      // Find the React component and set demoMode to false
      const appContainer = document.querySelector('[data-testid="app-container"]');
      if (appContainer) {
        // Trigger a state change by dispatching a custom event or using React dev tools
        // For now, we'll simulate the checkbox change
        const checkbox = document.querySelector('[data-testid="demo-mode-checkbox"]') as HTMLInputElement;
        if (checkbox && checkbox.checked) {
          checkbox.checked = false;
          // Dispatch change event to trigger React onChange
          const changeEvent = new Event('change', { bubbles: true });
          checkbox.dispatchEvent(changeEvent);
        }
      }
    });

    // Wait a bit for the state change to take effect
    await page.waitForTimeout(1000);

    // Setup provider and model
    await page.getByTestId("provider-select").selectOption("openai");
    await page.getByTestId("model-select").selectOption("gpt-4");

    // Enter some code
    await page.getByTestId("code-input").fill("function add(a, b) { return a + b; }");

    // Click run button
    await page.getByTestId("run-button").click();

    // Wait for execution plan to appear
    await expect(page.getByTestId("execution-plan")).toBeVisible();
    await expect(page.getByTestId("execution-plan-title")).toHaveText("Plan Preview");

    // Check that steps are displayed
    await expect(page.getByTestId("execution-steps")).toBeVisible();
    await expect(page.getByTestId("execution-step-step-1")).toBeVisible();
    await expect(page.getByTestId("execution-step-step-2")).toBeVisible();

    // Check step details
    await expect(page.getByTestId("execution-step-goblin-step-1")).toHaveText("docs-writer");
    await expect(page.getByTestId("execution-step-task-step-1")).toContainText("document this code");

    // Check streaming view appears
    await expect(page.getByTestId("streaming-view")).toBeVisible();
    await expect(page.getByTestId("streaming-title")).toHaveText("Streaming Output");
  });
});
