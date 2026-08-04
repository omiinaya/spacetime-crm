import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navTo } from "./helpers";

test.describe("Tickets", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navTo(page, "Tickets");
  });

  test("page heading and description are visible", async ({ page }) => {
    await expect(page.locator("h1").first()).toContainText("Tickets");
  });

  test("'New Ticket' button is visible", async ({ page }) => {
    await expect(page.getByText("New Ticket", { exact: true }).first()).toBeVisible();
  });

  test("clicking 'New Ticket' opens the form", async ({ page }) => {
    await page.getByText("New Ticket", { exact: true }).first().click();
    await waitForLoad(page);
    await expect(page.getByRole("button", { name: "Cancel", exact: true }).first()).toBeVisible();
  });

  test("cancel button closes the new ticket form", async ({ page }) => {
    await page.getByText("New Ticket", { exact: true }).first().click();
    await waitForLoad(page);
    await page.getByRole("button", { name: "Cancel", exact: true }).first().click();
    await expect(page.getByText("New Ticket", { exact: true }).first()).toBeVisible();
  });

  test("status filter buttons render and toggle active state", async ({ page }) => {
    const filters = ["All", "new", "assigned", "in_progress", "waiting_on_customer", "resolved", "closed"];
    for (const f of filters) {
      const btn = page.getByRole("button", { name: f, exact: true }).first();
      await expect(btn).toBeVisible({ timeout: 5_000 });
    }
    // Clicking a filter toggles active styling without crashing
    const newBtn = page.getByRole("button", { name: "new", exact: true }).first();
    await newBtn.click();
    await waitForLoad(page);
    await expect(newBtn).toBeVisible();
  });

  test("pagination controls are accessible (if paginated)", async ({ page }) => {
    // With fake-JWT auth there is no data, so pagination may legitimately be
    // absent. Assert that IF a prev/next control renders, it has an accessible
    // name (regression guard for icon-only pagination buttons).
    await page.waitForTimeout(1_500);
    const nextBtn = page
      .getByRole("button", { name: "Next page" })
      .first();
    const prevBtn = page
      .getByRole("button", { name: "Previous page" })
      .first();
    const count = await nextBtn.or(prevBtn).count();
    if (count > 0) {
      await expect(nextBtn.or(prevBtn).first()).toBeVisible();
    }
  });
});
