import { defineConfig } from "@playwright/test";

export default defineConfig({
	testDir: "./tests",
	timeout: 60_000, // Increased from 30_000 to 60_000 for slower async operations
	reporter: "line",
	use: {
		baseURL: "http://localhost:1420",
		headless: true,
		viewport: { width: 1280, height: 800 },
		channel: "chrome",
		trace: 'on-first-retry',
		screenshot: 'only-on-failure',
	},
	projects: [
		{
			name: "chromium",
			use: { channel: "chrome" },
		},
	],
});
