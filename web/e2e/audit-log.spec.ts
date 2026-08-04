import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navToSettingsTab } from "./helpers";

test.describe("Audit Log (Settings → Data)", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navToSettingsTab(page, "Data & Fields");
  });

  test("audit log section renders", async ({ page }) => {
    const main = page.locator("main");
    await expect(main.getByText(/audit/i).first()).toBeVisible();
  });

  test("data tab renders without errors", async ({ page }) => {
    await expect(page.locator("main")).toBeVisible();
    const body = page.locator("body");
    await expect(body).not.toContainText("Application Error", { useInnerText: true });
  });
});