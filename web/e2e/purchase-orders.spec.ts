import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navTo } from "./helpers";

test.describe("Purchase Orders", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navTo(page, "Purchase Orders");
  });

  test("page heading is visible", async ({ page }) => {
    await expect(page.locator("h1").first()).toContainText("Purchase Order");
  });

  test("'New PO' opens the form and cancels", async ({ page }) => {
    const btn = page.getByRole("button", { name: "New PO" }).first();
    await expect(btn).toBeVisible();
    await btn.click();
    await waitForLoad(page);
    const cancel = page.getByRole("button", { name: "Cancel", exact: true }).first();
    await expect(cancel).toBeVisible();
    await cancel.click();
    await expect(btn).toBeVisible();
  });
});