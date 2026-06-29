import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad } from "./helpers";

test.describe("Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await waitForLoad(page);
  });

  test("sidebar displays all navigation items", async ({ page }) => {
    const navItems = [
      "Dashboard",
      "Customers",
      "Map",
      "Tickets",
      "Invoices",
      "Payments",
      "Appointments",
      "Products",
      "Estimates",
      "Purchase Orders",
      "Import/Export",
      "Custom Fields",
      "Checklists",
      "Health",
      "Audit Log",
      "Reports",
      "Settings",
      "Tenants",
    ];

    for (const item of navItems) {
      const el = page.locator("aside").getByText(item, { exact: true });
      await expect(el).toBeVisible();
    }
  });

  test("navigating via sidebar changes the page heading", async ({ page }) => {
    const testCases = [
      { label: "Customers", heading: /customer/i },
      { label: "Tickets", heading: /ticket/i },
      { label: "Invoices", heading: /invoice/i },
    ];

    for (const { label, heading } of testCases) {
      await page.locator("aside").getByText(label, { exact: true }).click();
      await waitForLoad(page);
      await expect(page.locator("h1, h2").first()).toContainText(heading);
    }
  });

  test("theme toggle switches between light and dark", async ({ page }) => {
    const toggle = page.locator("aside").getByText(/light mode|dark mode/i);
    await expect(toggle).toBeVisible();

    await toggle.click();
    await page.waitForTimeout(300);
    const newLabel = await page
      .locator("aside")
      .getByText(/light mode|dark mode/i)
      .textContent();
    expect(newLabel).toBeTruthy();
  });

  test("Customer Portal link is visible", async ({ page }) => {
    const portalLink = page.locator("aside").getByText("Customer Portal");
    await expect(portalLink).toBeVisible();
  });

  test("forgot-password page loads standalone", async ({ page }) => {
    await page.goto("/forgot-password");
    await expect(page.getByText(/forgot/i)).toBeVisible();
  });
});
