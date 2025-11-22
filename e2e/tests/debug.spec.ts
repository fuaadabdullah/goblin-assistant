import { expect, test } from "@playwright/test";

test("debug page content", async ({ page }) => {
  // Listen for console messages
  page.on('console', msg => {
    console.log('PAGE CONSOLE:', msg.text());
  });

  await page.goto("/");
  await page.waitForTimeout(3000);

  // Check if the app is loaded
  const appContainer = page.locator('.app-container');
  const topControls = page.locator('.top-controls');
  console.log('App container exists:', await appContainer.isVisible().catch(() => false));
  console.log('Top controls exists:', await topControls.isVisible().catch(() => false));
  console.log('Top controls innerHTML:', await topControls.innerHTML().catch(() => 'error'));

  // Check for specific elements
  const providerSelect = page.locator('#provider-select');
  const modelSelect = page.locator('#model-select');
  const allDivsWithId = page.locator('div[id]');

  console.log('Provider select visible:', await providerSelect.isVisible().catch(() => false));
  console.log('Model select count:', await page.locator('#model-select').count());
  console.log('Model select visible:', await modelSelect.isVisible().catch(() => false));

  // List all divs with ids
  const divCount = await allDivsWithId.count();
  console.log('Number of divs with ids:', divCount);
  for (let i = 0; i < divCount; i++) {
    const div = allDivsWithId.nth(i);
    const id = await div.getAttribute('id').catch(() => 'no-id');
    console.log(`Div ${i}: id=${id}`);
  }

  // Get the selected value of provider select
  const selectedProvider = await providerSelect.inputValue().catch(() => 'error');
  console.log('Selected provider:', selectedProvider);

  // List all select elements
  const selects = page.locator('select');
  const selectCount = await selects.count();
  console.log('Number of select elements:', selectCount);

  for (let i = 0; i < selectCount; i++) {
    const select = selects.nth(i);
    const id = await select.getAttribute('id').catch(() => 'no-id');
    const value = await select.inputValue().catch(() => 'no-value');
    console.log(`Select ${i}: id=${id}, value=${value}`);
  }

  // Try selecting anthropic and see if model selector appears
  await providerSelect.selectOption("anthropic");
  await page.waitForTimeout(1000);
  console.log('After selecting anthropic - Model select visible:', await modelSelect.isVisible().catch(() => false));

  // Try selecting openai
  await providerSelect.selectOption("openai");
  await page.waitForTimeout(1000);
  console.log('After selecting openai - Model select visible:', await modelSelect.isVisible().catch(() => false));
});
