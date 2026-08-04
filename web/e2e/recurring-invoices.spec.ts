import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navToSubTab } from "./helpers";

test.describe("Recurring Invoices", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navToSubTab(page, "Invoices", "Recurring");
  });

  test("page heading is visible", async ({ page }) => {
    await expect(page.locator("h1").first()).toContainText("Recurring Invoices");
  });

  test("'New Rule' opens the rule form", async ({ page }) => {
    const btn = page.getByRole("button", { name: "New Rule" }).first();
    await expect(btn).toBeVisible();
    await btn.click();
    await waitForLoad(page);
    // The form's submit button is Create Rule (or Update Rule when editing)
    await expect(
      page.getByRole("button", { name: /create rule|update rule/i }).first()
    ).toBeVisible();
  });
});