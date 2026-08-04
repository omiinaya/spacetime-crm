import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navToSettingsTab } from "./helpers";

test.describe("Agent Access (Settings → System)", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navToSettingsTab(page, "System");
  });

  test("agent access section renders", async ({ page }) => {
    const main = page.locator("main");
    await expect(main.getByText(/agent access/i).first()).toBeVisible();
  });

  test("agent list area renders", async ({ page }) => {
    await expect(page.locator("main")).toBeVisible();
    const body = page.locator("body");
    await expect(body).not.toContainText("Application Error", { useInnerText: true });
  });
});