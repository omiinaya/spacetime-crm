import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad } from "./helpers";

test.describe("Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await waitForLoad(page);
  });

  test("shows the page title and heading", async ({ page }) => {
    await expect(page.locator("h1")).toContainText("Dashboard");
    await expect(page.getByText(/overview of your repair business/i)).toBeVisible();
  });

  test("displays all four summary cards with labels", async ({ page }) => {
    const labels = ["Total Customers", "Open Tickets", "Revenue", "Upcoming Appointments"];
    for (const label of labels) {
      const card = page.getByText(label, { exact: true });
      await expect(card).toBeVisible();
    }
  });

  test("summary cards are clickable and navigate to their respective pages", async ({ page }) => {
    const customersCard = page.getByText("Total Customers", { exact: true });
    await customersCard.click();
    await waitForLoad(page);
    await expect(page.locator("h1")).toContainText(/customer/i);
  });

  test("shows all quick action buttons", async ({ page }) => {
    const actions = ["New Customer", "New Ticket", "New Invoice", "New Appointment", "Add Product"];
    for (const action of actions) {
      const btn = page.locator("main").getByText(action, { exact: true });
      await expect(btn).toBeVisible();
    }
  });

  test("quick action buttons navigate to the correct page", async ({ page }) => {
    await page.locator("main").getByText("New Ticket", { exact: true }).click();
    await waitForLoad(page);
    await expect(page.locator("h1")).toContainText(/ticket/i);
  });

  test("shows the Recent Activity card", async ({ page }) => {
    const activityCard = page.getByText("Recent Activity", { exact: true });
    await expect(activityCard).toBeVisible();

    // Scoped within the activity card to avoid strict mode (2 elements match "open tickets")
    await expect(page.locator("p:has-text('Open tickets:')")).toBeVisible();
    await expect(page.locator("p:has-text('Pending revenue:')")).toBeVisible();
    await expect(page.locator("p:has-text('Total customers:')")).toBeVisible();
  });
});
