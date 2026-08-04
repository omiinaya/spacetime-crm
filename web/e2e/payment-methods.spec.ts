import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navToSubTab } from "./helpers";

test.describe("Payment Methods", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navToSubTab(page, "Payments", "Payment Methods");
  });

  test("page heading is visible", async ({ page }) => {
    await expect(page.locator("h1").first()).toContainText("Payment Methods");
  });

  test("page renders without errors", async ({ page }) => {
    await expect(page.locator("main")).toBeVisible();
    const body = page.locator("body");
    await expect(body).not.toContainText("Application Error", { useInnerText: true });
  });
});