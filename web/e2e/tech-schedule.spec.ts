import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navToSubTab } from "./helpers";

test.describe("Tech Schedule", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navToSubTab(page, "Appointments", "Tech Schedule");
  });

  test("page heading is visible", async ({ page }) => {
    await expect(page.locator("h1").first()).toContainText("Technician Schedule");
  });

  test("month navigation control is present", async ({ page }) => {
    // The calendar header shows the current month (e.g. "August 2026")
    const monthBtn = page.locator("main").getByText(/\w+ \d{4}/).first();
    await expect(monthBtn).toBeVisible();
  });

  test("empty state renders", async ({ page }) => {
    await expect(page.getByText(/no appointments scheduled/i).first()).toBeVisible({
      timeout: 5_000,
    });
  });
});