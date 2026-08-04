import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navToSettingsTab } from "./helpers";

test.describe("Tenants (Settings → System)", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navToSettingsTab(page, "System");
  });

  test("tenant section renders", async ({ page }) => {
    const main = page.locator("main");
    await expect(main.getByText("Tenants", { exact: true }).first()).toBeVisible();
  });

  test("'New Tenant' opens the creation form", async ({ page }) => {
    const btn = page.getByRole("button", { name: "New Tenant" }).first();
    await expect(btn).toBeVisible({ timeout: 5_000 });
    await btn.click();
    await waitForLoad(page);
    await expect(page.locator("main").getByRole("heading", { name: "Create Tenant" })).toBeVisible();
  });
});