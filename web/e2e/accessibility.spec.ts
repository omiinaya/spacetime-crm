import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navTo } from "./helpers";

// Block the PWA service worker: it intercepts /api/ with NetworkFirst and
// serves cached responses itself, which would bypass page.route() mocks and
// hide the real backend 401s that these UI-structure tests rely on.
test.use({ contextOptions: { serviceWorkers: "block" } });

// Regression protection for accessibility fixes: icon-only buttons must expose
// an accessible name (aria-label) so screen readers / keyboard users can navigate.
// API responses are mocked so data-dependent components actually render.
test.describe("Accessibility — icon-only buttons have accessible names", () => {
  test("POS 'Add to cart' product buttons are labeled", async ({ page }) => {
    await page.route("**/api/products*", (route) => {
      const url = new URL(route.request().url());
      // Only mock the product LIST endpoint; let everything else pass through.
      if (url.pathname !== "/api/products") {
        return route.continue();
      }
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          products: [
            {
              id: "prod_1",
              name: "Test Product",
              sku: "TP-001",
              price: 19.99,
              cost: 5,
              quantity: 10,
              item_type: "part",
              tax_rate: 0,
              currency: "USD",
              location: "Shelf A",
            },
          ],
          total: 1,
        }),
      });
    });
    await loginAs(page, "admin");
    await navTo(page, "POS");
    await waitForLoad(page);
    await page.getByPlaceholder(/scan barcode or search products/i).fill("Test");
    const addBtn = page
      .getByRole("button", { name: "Add to cart" })
      .first();
    await expect(addBtn).toBeVisible({ timeout: 10_000 });
  });

  test("previous/next month on Tech Schedule are labeled", async ({ page }) => {
    await loginAs(page, "admin");
    await navTo(page, "Appointments");
    await page.getByRole("tab", { name: "Tech Schedule", exact: true }).click();
    await waitForLoad(page);
    await expect(
      page.getByRole("button", { name: "Previous month" }).first()
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Next month" }).first()
    ).toBeVisible();
  });

  test("pagination prev/next are labeled", async ({ page }) => {
    // Return 30 customers so pagination controls render (page size is 25).
    const customers = Array.from({ length: 30 }, (_, i) => ({
      id: `cust_${i}`,
      first_name: `First${i}`,
      last_name: `Last${i}`,
      email: `cust${i}@example.com`,
      phone: "",
      company: "",
      address: "",
      city: "",
      state: "",
      zip: "",
      country: "US",
      created_at: "2026-08-01T00:00:00Z",
      updated_at: "2026-08-01T00:00:00Z",
      tenant_id: "t1",
    }));
    await page.route("**/api/customers*", (route) => {
      const url = new URL(route.request().url());
      // Only mock the customer LIST endpoint; let sub-routes (duplicates,
      // geolocations, portal-password) pass through untouched.
      if (url.pathname !== "/api/customers") {
        return route.continue();
      }
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ customers, total: 30 }),
      });
    });
    await loginAs(page, "admin");
    await navTo(page, "Customers");
    await waitForLoad(page);
    await expect(
      page.getByRole("button", { name: "Previous page" }).first()
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Next page" }).first()
    ).toBeVisible();
  });

  test("every page exposes at least one top-level h1 heading", async ({ page }) => {
    const pages: Array<[string, string]> = [
      ["Customers", "Customers"],
      ["Tickets", "Tickets"],
      ["Invoices", "Invoices"],
      ["Payments", "Payments"],
      ["POS", "Point of Sale"],
    ];
    for (const [label, title] of pages) {
      await loginAs(page, "admin");
      await navTo(page, label);
      await waitForLoad(page);
      const h1Count = await page.locator("h1").count();
      expect(h1Count, `${title} should have an h1`).toBeGreaterThanOrEqual(1);
    }
  });
});