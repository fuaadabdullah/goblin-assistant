/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
    exclude: ['e2e/**', 'node_modules/**'],
  },
  // Path aliases for clean imports (same as vite.config.ts)
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
  // Define environment variables for tests
  define: {
    'import.meta.env.VITE_FASTAPI_URL': JSON.stringify('http://127.0.0.1:8000'),
    'import.meta.env.VITE_GOBLIN_RUNTIME': JSON.stringify('fastapi'),
    'import.meta.env.VITE_MOCK_API': JSON.stringify('false'),
  },
})
