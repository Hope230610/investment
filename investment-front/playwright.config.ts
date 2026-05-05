import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E test configuration.
 *
 * Required env vars (set in .env or CI environment):
 *   E2E_BASE_URL        — Frontend URL (default: http://localhost:3000)
 *   E2E_API_URL         — Backend API URL (default: http://localhost:8000)
 *   E2E_USER            — Test username (default: testuser)
 *   E2E_PASS            — Test password (default: testpassword123)
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,           // Avoid DB conflicts when tests write learning history
  forbidOnly: !!process.env.CI,  // Fail CI if test.skip() or test.fixme() remains
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [['github']] : [['list']],
  globalTimeout: 12 * 60_000,
  webServer: [
    {
      command: 'cd ../investment-back && python -m uvicorn main:app --host 0.0.0.0 --port 8000',
      url: process.env['E2E_API_URL'] ?? 'http://localhost:8000/api/v1/docs',
      reuseExistingServer: process.env['E2E_REUSE_SERVERS'] !== 'false',
      timeout: 60_000,
      env: {
        ...process.env,
        DEBUG: 'true',
        ENVIRONMENT: 'development',
      },
    },
    {
      command: 'npm run dev',
      url: process.env['E2E_BASE_URL'] ?? 'http://localhost:3000',
      reuseExistingServer: process.env['E2E_REUSE_SERVERS'] !== 'false',
      timeout: 60_000,
    },
  ],

  use: {
    baseURL: process.env['E2E_BASE_URL'] ?? 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  timeout: 90_000,   // Per-test timeout; real market-data analysis can exceed 30s
});
