import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navToSettingsTab } from "./helpers";

test.describe("Health (Settings → System)", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navToSettingsTab(page, "System");
  });

  test("health heading is visible", async ({ page }) => {
    await expect(page.locator("main").getByText(/health/i).first()).toBeVisible();
  });

  test("system tab renders without errors", async ({ page }) => {
    await expect(page.locator("main")).toBeVisible();
    const body = page.locator("body");
    await expect(body).not.toContainText("Application Error", { useInnerText: true });
  });
});