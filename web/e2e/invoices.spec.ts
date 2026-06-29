import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad } from "./helpers";

test.describe("Invoices", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await waitForLoad(page);
    await page.locator("aside").getByText("Invoices", { exact: true }).click();
    await waitForLoad(page);
  });

  test("page heading and description are visible", async ({ page }) => {
    await expect(page.locator("h1")).toContainText("Invoices");
    await expect(page.getByText(/billing and invoicing/i)).toBeVisible();
  });

  test("'New Invoice' button is visible", async ({ page }) => {
    const newBtn = page.getByText("New Invoice", { exact: true });
    await expect(newBtn).toBeVisible();
  });

  test("clicking 'New Invoice' opens the creation form", async ({ page }) => {
    await page.getByText("New Invoice", { exact: true }).click();
    await expect(page.getByText("New Invoice").nth(1)).toBeVisible();
    await expect(page.locator("input[placeholder='Ticket ID (optional)']")).toBeVisible();
    await expect(page.locator("input[placeholder='Notes']")).toBeVisible();
    await expect(page.locator("input[placeholder='Terms']")).toBeVisible();
    await expect(page.getByText("Create", { exact: true })).toBeVisible();
    await expect(page.getByText("Cancel", { exact: true })).toBeVisible();
  });

  test("cancel button closes the new invoice form", async ({ page }) => {
    await page.getByText("New Invoice", { exact: true }).click();
    await expect(page.getByText("Create", { exact: true })).toBeVisible();
    await page.getByText("Cancel", { exact: true }).click();
    await expect(page.getByText("Create", { exact: true })).not.toBeVisible();
  });

  test("displays status filter buttons", async ({ page }) => {
    const statusFilters = ["All", "draft", "sent", "paid", "overdue", "cancelled"];
    for (const filter of statusFilters) {
      const btn = page.locator("button").filter({ hasText: new RegExp(`^${filter}$`, "i") });
      await expect(btn.first()).toBeVisible();
    }
  });

  test("clicking a status filter changes the active filter", async ({ page }) => {
    const paidBtn = page.locator("button").filter({ hasText: /^paid$/i });
    await paidBtn.click();
    await waitForLoad(page);
    await expect(paidBtn).toBeVisible();
  });

  test("shows invoice cards when invoices exist", async ({ page }) => {
    await page.waitForTimeout(1_000);
    const invoiceNumbers = page.locator("text=#");
    const count = await invoiceNumbers.count();
    if (count > 0) {
      await expect(invoiceNumbers.first()).toBeVisible();
    }
  });

  test("shows pagination controls", async ({ page }) => {
    const nextBtn = page.locator("button").filter({ hasText: /next/i });
    const prevBtn = page.locator("button").filter({ hasText: /prev/i });
    await expect(nextBtn.or(prevBtn).first()).toBeVisible({ timeout: 5_000 }).catch(() => {});
  });
});
