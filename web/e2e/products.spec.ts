import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navTo } from "./helpers";

test.describe("Products", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navTo(page, "Products");
  });

  test("page heading is visible", async ({ page }) => {
    await expect(page.locator("h1").first()).toContainText("Products");
  });

  test("add product form opens and cancels", async ({ page }) => {
    const addBtn = page.getByRole("button", { name: /add product/i }).first();
    await expect(addBtn).toBeVisible();
    await addBtn.click();
    await waitForLoad(page);
    await expect(
      page.getByRole("button", { name: "Cancel", exact: true }).first()
    ).toBeVisible();
    await page.getByRole("button", { name: "Cancel", exact: true }).first().click();
    await expect(
      page.getByRole("button", { name: /add product/i }).first()
    ).toBeVisible();
  });

  test("inventory controls are present", async ({ page }) => {
    // Available without data: Count Sheet and the empty-state CTA
    await expect(page.getByRole("button", { name: "Count Sheet" }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "New Product" }).first()).toBeVisible();
  });
});