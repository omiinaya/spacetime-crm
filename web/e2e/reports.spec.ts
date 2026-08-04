import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navTo } from "./helpers";

test.describe("Reports", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navTo(page, "Reports");
  });

  test("page renders without errors", async ({ page }) => {
    await expect(page.locator("main")).toBeVisible();
    const body = page.locator("body");
    await expect(body).not.toContainText("Application Error", { useInnerText: true });
  });

  test("graceful error state when reports fail to load", async ({ page }) => {
    // Without a valid backend session the reports endpoint 401s — the page
    // must degrade gracefully instead of crashing.
    await expect(page.getByText("Failed to load reports.").first()).toBeVisible({
      timeout: 10_000,
    });
  });
});