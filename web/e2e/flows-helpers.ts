import { Page } from "@playwright/test";

/**
 * Real-login helpers for full-stack flow tests.
 *
 * Unlike `loginAs()` (which injects a fake JWT so pages render but every API
 * call 401s), these helpers authenticate through the REAL login form against
 * the live FastAPI backend + SpacetimeDB, so CRUD flows round-trip through
 * the entire stack.
 *
 * The seeded admin account (scripts/bootstrap.py) is admin@crm.local / admin123.
 * Tests that mutate data must use unique names (Date.now()) so they never
 * collide with each other or with seeded rows.
 */

export const FLOW_ADMIN = {
  email: "admin@crm.local",
  password: "admin123",
};

export const unique = (prefix: string) =>
  `${prefix}-${Date.now()}-${Math.floor(Math.random() * 10000)}`;

/**
 * Perform a real login through the UI login form and wait for the app shell.
 */
export async function loginReal(
  page: Page,
  email = FLOW_ADMIN.email,
  password = FLOW_ADMIN.password
) {
  await page.goto("/");
  // If already logged in (persisted token), skip.
  const already = await page.locator("aside").count();
  if (already > 0) return;
  await page.getByPlaceholder("admin@repairshop.com").fill(email);
  await page.getByPlaceholder("Enter your password").fill(password);
  await page.getByRole("button", { name: /sign in/i }).click();
  // Wait for the app shell (sidebar) to appear — login round-trips through the API.
  await page.locator("aside").first().waitFor({ timeout: 20_000 });
  // Wait for the post-login redirect to settle.
  await page.waitForLoadState("networkidle").catch(() => {});
}

/**
 * Navigate to a sidebar page using the grouped nav labels.
 */
export async function navToFlow(page: Page, label: string) {
  await page.locator("aside").getByText(label, { exact: true }).click();
  await page.waitForLoadState("networkidle").catch(() => {});
}

/**
 * Assert the user is signed out (login form visible).
 */
export async function expectSignedOut(page: Page) {
  await page.getByRole("button", { name: /sign in/i }).first().waitFor({
    timeout: 10_000,
  });
}
