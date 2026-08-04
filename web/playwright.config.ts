import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E configuration for SpacetimeCRM.
 *
 * The frontend dev server runs on port 5185 (see vite.config.ts).
 * The FastAPI backend is expected at http://localhost:8723 (proxied via Vite).
 *
 * Usage:
 *   npm run test:e2e          # run all e2e tests
 *   npm run test:e2e -- --ui  # interactive UI mode
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  // Always a single worker: multiple workers sharing one Vite dev server
  // cause concurrent transform contention → timeouts (documented pitfall).
  workers: 1,
  timeout: 90_000,
  reporter: [[process.env.CI ? "github" : "list"]],
  use: {
    baseURL: "http://localhost:5185",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  /* Run the Vite dev server before tests in development */
  webServer: process.env.CI
    ? undefined
    : {
        command: "npm run dev",
        url: "http://localhost:5185",
        reuseExistingServer: !process.env.CI,
        timeout: 60_000,
      },
});
