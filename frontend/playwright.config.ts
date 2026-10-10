import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright configuration for OpsCommand end-to-end tests.
 *
 * The e2e suite drives the real frontend against the real backend. The full
 * stack (Postgres, Redis, backend API, Celery worker) must be running before
 * `npm run test:e2e`. The frontend dev server is started automatically via
 * `webServer` (reused if already running). See docs/testing.md for the exact
 * commands to bring up the stack.
 */
export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? 'github' : 'list',
  timeout: 90_000,
  expect: { timeout: 10_000 },
  outputDir: 'test-results',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: process.env.E2E_BASE_URL || 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 60_000,
    env: {
      VITE_API_BASE_URL: 'http://localhost:8000',
      VITE_WS_URL: 'ws://localhost:8000',
    },
  },
})
