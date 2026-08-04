import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navTo } from "./helpers";

test.describe("Email Campaigns", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navTo(page, "Email Campaigns");
  });

  test("page renders without errors", async ({ page }) => {
    await expect(page.locator("main")).toBeVisible();
    const body = page.locator("body");
    await expect(body).not.toContainText("Application Error", { useInnerText: true });
  });

  test("campaign template controls exist", async ({ page }) => {
    // Templates are bundled in the app — always visible
    const template = page
      .locator("main")
      .getByRole("button", { name: /promotional offer|service reminder|seasonal greeting/i })
      .first();
    await expect(template).toBeVisible();
  });
});