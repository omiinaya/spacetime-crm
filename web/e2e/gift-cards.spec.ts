import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navToSubTab } from "./helpers";

test.describe("Gift Cards", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navToSubTab(page, "Payments", "Gift Cards");
  });

  test("page heading is visible", async ({ page }) => {
    await expect(page.locator("h1, h2").first()).toContainText("Gift Cards");
  });

  test("'New Gift Card' button is visible", async ({ page }) => {
    await expect(page.getByRole("button", { name: "New Gift Card" }).first()).toBeVisible();
  });

  test("status filter buttons exist", async ({ page }) => {
    for (const name of ["All", "Active", "Voided"]) {
      const btn = page.getByRole("button", { name, exact: true }).first();
      await expect(btn).toBeVisible({ timeout: 5_000 });
    }
  });

  test("gift card lookup input exists", async ({ page }) => {
    await expect(
      page.getByPlaceholder("Enter gift card code").first()
    ).toBeVisible();
  });
});