import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import path from "path";

// https://vite.dev/config/
export default defineConfig(async () => ({
	plugins: [react()],

	// Enable sourcemaps for debugging
	build: { sourcemap: true },

	server: {
		port: 3000,
		strictPort: false,
	},

	// Path aliases for clean imports
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "./src"),
			"@components": path.resolve(__dirname, "./src/components"),
			"@pages": path.resolve(__dirname, "./src/pages"),
			"@api": path.resolve(__dirname, "./src/api"),
			"@utils": path.resolve(__dirname, "./src/utils"),
			"@types": path.resolve(__dirname, "./src/types"),
			"@hooks": path.resolve(__dirname, "./src/hooks"),
			"@assets": path.resolve(__dirname, "./src/assets"),
		},
	},
}));

