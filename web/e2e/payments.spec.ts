import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navTo } from "./helpers";

test.describe("Payments", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navTo(page, "Payments");
  });

  test("page heading is visible", async ({ page }) => {
    await expect(page.locator("h1").first()).toContainText("Payments");
  });

  test("record payment form opens and cancels", async ({ page }) => {
    const record = page.getByRole("button", { name: "Record Payment" }).first();
    await expect(record).toBeVisible();
    await record.click();
    await waitForLoad(page);
    await expect(
      page.getByRole("button", { name: "Cancel", exact: true }).first()
    ).toBeVisible();
    await page.getByRole("button", { name: "Cancel", exact: true }).first().click();
    await expect(record).toBeVisible();
  });
});