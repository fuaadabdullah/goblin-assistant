import { expect, test } from "@playwright/test";

test("check model selector", async ({ page }) => {
  const consoleMessages: string[] = [];
  const errors: string[] = [];

  page.on('console', msg => {
    consoleMessages.push(msg.text());
  });

  page.on('pageerror', error => {
    errors.push(error.message);
  });

  await page.goto(`/?t=${Date.now()}`);
  await page.waitForTimeout(2000);

  // Take a screenshot
  await page.screenshot({ path: 'debug-screenshot.png', fullPage: true });

  // Check page title and basic content
  const title = await page.title();
  console.log('Page title:', title);

  const bodyText = await page.locator('body').textContent();
  console.log('Body text length:', bodyText?.length || 0);

  // Check if root div exists
  const rootDiv = page.locator('#root');
  const rootExists = await rootDiv.isVisible().catch(() => false);
  console.log('Root div exists:', rootExists);

  if (rootExists) {
    const rootHtml = await rootDiv.innerHTML();
    console.log('Root div HTML length:', rootHtml.length);
    console.log('Root div HTML preview:', rootHtml.substring(0, 200));
  }
});
