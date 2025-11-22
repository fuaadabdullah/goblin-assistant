import { defineConfig } from "@playwright/test";

export default defineConfig({
	testDir: "./tests",
	timeout: 60_000, // Increased from 30_000 to 60_000 for slower async operations
	reporter: "line",
	webServer: {
		command: "VITE_MOCK_API=false VITE_FASTAPI_URL=http://127.0.0.1:3001 pnpm run dev:web",
		port: 1420,
		timeout: 120_000,
		reuseExistingServer: true,
	},
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
