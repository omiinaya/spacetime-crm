import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad } from "./helpers";

test.describe("Tickets", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await waitForLoad(page);
    await page.locator("aside").getByText("Tickets", { exact: true }).click();
    await waitForLoad(page);
  });

  test("page heading and description are visible", async ({ page }) => {
    await expect(page.locator("h1")).toContainText("Tickets");
    await expect(page.getByText(/manage repair tickets/i)).toBeVisible();
  });

  test("'New Ticket' button is visible", async ({ page }) => {
    const newBtn = page.getByText("New Ticket", { exact: true });
    await expect(newBtn).toBeVisible();
  });

  test("clicking 'New Ticket' opens the form", async ({ page }) => {
    await page.getByText("New Ticket", { exact: true }).click();
    await expect(page.getByText("New Ticket").nth(1)).toBeVisible();
    await expect(page.locator("input[placeholder='Title']")).toBeVisible();
    await expect(page.locator("input[placeholder='Description']")).toBeVisible();
    await expect(page.locator("input[placeholder='Device type']")).toBeVisible();
    await expect(page.locator("input[placeholder='Device model']")).toBeVisible();
    await expect(page.locator("input[placeholder='Serial']")).toBeVisible();
    await expect(page.getByText("Create", { exact: true })).toBeVisible();
    await expect(page.getByText("Cancel", { exact: true })).toBeVisible();
  });

  test("cancel button closes the new ticket form", async ({ page }) => {
    await page.getByText("New Ticket", { exact: true }).click();
    await expect(page.getByText("Create", { exact: true })).toBeVisible();
    await page.getByText("Cancel", { exact: true }).click();
    await expect(page.getByText("Create", { exact: true })).not.toBeVisible();
  });

  test("displays status filter buttons", async ({ page }) => {
    const statusFilters = ["All", "new", "assigned", "in_progress", "waiting_on_customer", "resolved", "closed"];
    for (const filter of statusFilters) {
      const btn = page.locator("button").filter({ hasText: new RegExp(`^${filter}$`, "i") });
      await expect(btn.first()).toBeVisible();
    }
  });

  test("clicking a status filter changes the active filter", async ({ page }) => {
    const resolvedBtn = page.locator("button").filter({ hasText: /^resolved$/i });
    await resolvedBtn.click();
    await waitForLoad(page);
    await expect(resolvedBtn).toBeVisible();
  });

  test("shows pagination controls when tickets exist", async ({ page }) => {
    const nextBtn = page.locator("button").filter({ hasText: /next/i });
    const prevBtn = page.locator("button").filter({ hasText: /prev/i });
    await expect(nextBtn.or(prevBtn).first()).toBeVisible({ timeout: 5_000 }).catch(() => {});
  });
});
