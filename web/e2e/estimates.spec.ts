import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navTo } from "./helpers";

test.describe("Estimates", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navTo(page, "Estimates");
  });

  test("page heading is visible", async ({ page }) => {
    await expect(page.locator("h1").first()).toContainText("Estimates");
  });

  test("'New Estimate' opens the form and cancels", async ({ page }) => {
    const btn = page.getByRole("button", { name: "New Estimate" }).first();
    await expect(btn).toBeVisible();
    await btn.click();
    await waitForLoad(page);
    const cancel = page.getByRole("button", { name: "Cancel", exact: true }).first();
    await expect(cancel).toBeVisible();
    await cancel.click();
    await expect(btn).toBeVisible();
  });

  test("status filter buttons render", async ({ page }) => {
    for (const name of ["All", "draft", "sent", "approved", "declined"]) {
      const btn = page.getByRole("button", { name, exact: true }).first();
      await expect(btn).toBeVisible({ timeout: 5_000 });
    }
  });
});