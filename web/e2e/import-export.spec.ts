import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navToSettingsTab } from "./helpers";

test.describe("Import / Export (Settings → Data)", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navToSettingsTab(page, "Data & Fields");
  });

  test("page heading is visible", async ({ page }) => {
    await expect(page.locator("main").getByText(/import/i).first()).toBeVisible();
  });

  test("export and import sections render", async ({ page }) => {
    const main = page.locator("main");
    await expect(main.getByText(/export/i).first()).toBeVisible();
    await expect(main.getByText(/import/i).first()).toBeVisible();
  });
});