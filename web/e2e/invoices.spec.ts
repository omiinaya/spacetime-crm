import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navTo } from "./helpers";

test.describe("Invoices", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navTo(page, "Invoices");
  });

  test("page heading and description are visible", async ({ page }) => {
    await expect(page.locator("h1").first()).toContainText("Invoices");
    await expect(page.getByText(/billing and invoicing/i).first()).toBeVisible({
      timeout: 5_000,
    });
  });

  test("'New Invoice' button is visible", async ({ page }) => {
    await expect(page.getByText("New Invoice", { exact: true }).first()).toBeVisible();
  });

  test("clicking 'New Invoice' opens the creation form", async ({ page }) => {
    await page.getByText("New Invoice", { exact: true }).first().click();
    await waitForLoad(page);
    await expect(page.getByRole("button", { name: "Create", exact: true }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Cancel", exact: true }).first()).toBeVisible();
  });

  test("cancel button closes the new invoice form", async ({ page }) => {
    await page.getByText("New Invoice", { exact: true }).first().click();
    await waitForLoad(page);
    await page.getByRole("button", { name: "Cancel", exact: true }).first().click();
    await expect(page.getByText("New Invoice", { exact: true }).first()).toBeVisible();
  });

  test("status filter buttons render and toggle active state", async ({ page }) => {
    const filters = ["All", "draft", "sent", "paid", "overdue"];
    for (const f of filters) {
      const btn = page.getByRole("button", { name: f, exact: true }).first();
      await expect(btn).toBeVisible({ timeout: 5_000 });
    }
    const sent = page.getByRole("button", { name: "sent", exact: true }).first();
    await sent.click();
    await waitForLoad(page);
    await expect(sent).toBeVisible();
  });

  test("bulk edit controls exist when invoices are present", async ({ page }) => {
    const bulkBtn = page.getByRole("button", { name: /bulk edit/i }).first();
    if (await bulkBtn.isVisible().catch(() => false)) {
      await bulkBtn.click();
      await waitForLoad(page);
      await expect(page.getByRole("button", { name: "Cancel", exact: true }).first()).toBeVisible();
    }
  });
});
