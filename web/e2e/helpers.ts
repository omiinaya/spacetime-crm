import { Page } from "@playwright/test";

/**
 * Create a fake JWT that the app will decode for auth testing.
 * The app extracts: sub, name, email, role from the payload.
 */
export function makeFakeToken(overrides?: Record<string, string>): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = btoa(
    JSON.stringify({
      sub: "usr_test",
      name: "Test Admin",
      email: "admin@repairshop.com",
      role: "admin",
      ...overrides,
    })
  );
  const dummySig = btoa("dummy_signature");
  return `${header}.${payload}.${dummySig}`;
}

/**
 * Set up localStorage with a valid-looking JWT so the app treats
 * the user as authenticated. Must navigate to the app origin first
 * (about:blank blocks localStorage).
 */
export async function loginAs(page: Page, role = "admin") {
  // Navigate to the app first so localStorage is accessible (about:blank blocks it)
  await page.goto("/");
  await page.evaluate(
    ({ token }) => {
      localStorage.setItem("crm_token", token);
    },
    { token: makeFakeToken({ role }) }
  );
  // Reload so React picks up the token from localStorage
  await page.reload();
}

/**
 * Navigate to a page via the sidebar and wait for it to settle.
 */
export async function navTo(page: Page, label: string) {
  await page.locator("aside").getByText(label, { exact: true }).click();
  await waitForLoad(page);
}

/**
 * Navigate to a Settings tab (Settings is admin-only, single sidebar entry,
 * with internal tabs: General / Notifications / Business / Data & Fields / System).
 */
export async function navToSettingsTab(page: Page, tabLabel: string) {
  await navTo(page, "Settings");
  const tab = page.getByRole("tab", { name: tabLabel, exact: true });
  await tab.click();
  await waitForLoad(page);
}

/**
 * Navigate to a sub-tab of a parent page (e.g. Payments → "Gift Cards",
 * Invoices → "Recurring", Customers → "Map").
 */
export async function navToSubTab(page: Page, parentLabel: string, subLabel: string) {
  await navTo(page, parentLabel);
  const tab = page.getByRole("tab", { name: subLabel, exact: true });
  await tab.click();
  await waitForLoad(page);
}

/**
 * Returns true if the page shows a spinner/loading indicator.
 */
export async function isLoadingVisible(page: Page): Promise<boolean> {
  return page.locator(".animate-spin").first().isVisible().catch(() => false);
}

/**
 * Wait for loading to finish (spinner disappears, or content appears).
 * Tolerant: never throws — returns after settling or the grace window.
 */
export async function waitForLoad(page: Page, timeoutMs = 15_000) {
  // Give React a tick to render
  await page.waitForTimeout(500);
  // If a spinner is visible, wait for it to go away
  const spinner = page.locator(".animate-spin").first();
  if (await spinner.isVisible({ timeout: 500 }).catch(() => false)) {
    await spinner.waitFor({ state: "hidden", timeout: timeoutMs }).catch(() => {});
  }
  // Give the page a beat to settle after the spinner clears
  await page.waitForTimeout(300);
}
