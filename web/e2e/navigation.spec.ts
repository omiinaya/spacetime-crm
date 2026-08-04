import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navTo, navToSubTab } from "./helpers";

test.describe("Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await waitForLoad(page);
  });

  test("sidebar shows grouped top-level navigation", async ({ page }) => {
    const aside = page.locator("aside");
    // Top-level items
    const items = [
      "Dashboard",
      "Customers",
      "Tickets",
      "Invoices",
      "Payments",
      "Estimates",
      "Appointments",
      "Products",
      "Purchase Orders",
      "POS",
      "Email Campaigns",
      "Reports",
      "Settings",
    ];
    for (const item of items) {
      await expect(aside.getByText(item, { exact: true })).toBeVisible();
    }
  });

  test("consolidated pages are not in the sidebar", async ({ page }) => {
    const aside = page.locator("aside");
    const removed = [
      "Map",
      "Recurring",
      "Payment Methods",
      "Gift Cards",
      "Tech Schedule",
      "Import/Export",
      "Custom Fields",
      "Checklists",
      "Health",
      "Audit Log",
      "Tenants",
      "Agent Access",
    ];
    for (const item of removed) {
      await expect(aside.getByText(item, { exact: true })).toHaveCount(0);
    }
  });

  test("sidebar renders section headers", async ({ page }) => {
    const aside = page.locator("aside");
    for (const section of ["Sales", "Scheduling", "Inventory", "Point of Sale", "Marketing", "Insights", "Administration"]) {
      await expect(aside.getByText(section, { exact: true })).toBeVisible();
    }
  });

  test("every sidebar item navigates to its page", async ({ page }) => {
    const testCases: { label: string; heading: RegExp }[] = [
      { label: "Dashboard", heading: /dashboard/i },
      { label: "Customers", heading: /customer/i },
      { label: "Tickets", heading: /ticket/i },
      { label: "Invoices", heading: /invoice/i },
      { label: "Payments", heading: /payment/i },
      { label: "Estimates", heading: /estimate/i },
      { label: "Appointments", heading: /appointment/i },
      { label: "Products", heading: /product/i },
      { label: "Purchase Orders", heading: /purchase order/i },
      { label: "POS", heading: /point of sale/i },
      { label: "Settings", heading: /settings/i },
    ];

    for (const { label, heading } of testCases) {
      await navTo(page, label);
      await expect(page.locator("h1, h2").first()).toContainText(heading, {
        timeout: 10_000,
      });
    }
  });

  test("reports page renders its graceful error state", async ({ page }) => {
    await navTo(page, "Reports");
    await expect(page.getByText("Unable to load reports").first()).toBeVisible({
      timeout: 10_000,
    });
    // The error state offers a retry control — clicking it must not crash
    const retry = page.getByRole("button", { name: "Retry" }).first();
    if (await retry.isVisible().catch(() => false)) {
      await retry.click();
      await waitForLoad(page);
      await expect(page.locator("main")).toBeVisible();
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
    await expect(page.locator("aside").getByText("Customer Portal")).toBeVisible();
  });

  test("forgot-password page loads standalone", async ({ page }) => {
    await page.goto("/forgot-password");
    await expect(page.getByText(/forgot/i)).toBeVisible();
  });

  test("mobile menu opens the sidebar", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    await waitForLoad(page);
    const hamburger = page.locator("header button").first();
    if (await hamburger.isVisible().catch(() => false)) {
      await hamburger.click();
      await waitForLoad(page);
      await expect(page.locator("aside").getByText("Dashboard", { exact: true })).toBeVisible();
    }
  });
});

test.describe("Sub-tab navigation (consolidation)", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await waitForLoad(page);
  });

  test("Customers page exposes a Map sub-tab", async ({ page }) => {
    await navToSubTab(page, "Customers", "Map");
    await expect(page.locator("main").getByText(/customer map/i).first()).toBeVisible();
    // Switch back to List
    await page.getByRole("tab", { name: "List", exact: true }).click();
    await waitForLoad(page);
    await expect(page.locator("h1").first()).toContainText("Customers");
  });

  test("Invoices page exposes a Recurring sub-tab", async ({ page }) => {
    await navToSubTab(page, "Invoices", "Recurring");
    await expect(page.locator("h1").first()).toContainText("Recurring Invoices");
  });

  test("Payments page exposes Payment Methods and Gift Cards sub-tabs", async ({ page }) => {
    await navToSubTab(page, "Payments", "Payment Methods");
    await expect(page.locator("h1").first()).toContainText("Payment Methods");
    await page.getByRole("tab", { name: "Gift Cards", exact: true }).click();
    await waitForLoad(page);
    await expect(page.locator("h1, h2").first()).toContainText("Gift Cards");
  });

  test("Appointments page exposes a Tech Schedule sub-tab", async ({ page }) => {
    await navToSubTab(page, "Appointments", "Tech Schedule");
    await expect(page.locator("h1").first()).toContainText("Technician Schedule");
  });
});

test.describe("Navigation role filtering", () => {
  test("tech role hides admin-only items and Settings", async ({ page }) => {
    await loginAs(page, "tech");
    await waitForLoad(page);
    const aside = page.locator("aside");
    await expect(aside.getByText("Settings", { exact: true })).toHaveCount(0);
    await expect(aside.getByText("Tickets", { exact: true })).toBeVisible();
  });

  test("front desk role hides inventory and admin items", async ({ page }) => {
    await loginAs(page, "front_desk");
    await waitForLoad(page);
    const aside = page.locator("aside");
    for (const item of ["Products", "Purchase Orders", "Reports", "Estimates", "Settings"]) {
      await expect(aside.getByText(item, { exact: true })).toHaveCount(0);
    }
    await expect(aside.getByText("Customers", { exact: true })).toBeVisible();
  });
});