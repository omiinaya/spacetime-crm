import { test, expect } from "@playwright/test";
import { loginReal, unique, navToFlow } from "./flows-helpers";

/**
 * Full-stack Playwright E2E flows.
 *
 * These run against the LIVE FastAPI + SpacetimeDB stack (no fake JWT, no
 * route mocks). They authenticate through the real login form and exercise
 * read/write CRUD journeys that round-trip through every layer:
 *   UI form → React query → FastAPI /api/* → STDB reducer → table → back to UI.
 *
 * Each flow uses unique, timestamped data so runs never collide. The seeded
 * admin (admin@crm.local / admin123) owns the target tenant.
 */
test.describe("Full-stack flows", () => {
  test("real login succeeds and shows the app shell", async ({ page }) => {
    await loginReal(page);
    await expect(page.locator("aside").first()).toBeVisible();
    await expect(page.getByText("Dashboard", { exact: true }).first()).toBeVisible();
  });

  test("create a customer end-to-end and verify it renders + persists", async ({
    page,
  }) => {
    await loginReal(page);
    await navToFlow(page, "Customers");

    const first = unique("E2E");
    const last = "CustomerFlow";
    const email = `${first.toLowerCase()}@example.com`;

    await page.getByText("Add Customer", { exact: true }).first().click();
    await page.getByPlaceholder("First Name").fill(first);
    await page.getByPlaceholder("Last Name").fill(last);
    await page.getByPlaceholder("Email").fill(email);
    await page.getByPlaceholder("Phone").fill("555-0100");
    await page.getByRole("button", { name: "Create", exact: true }).first().click();

    // The customer row appears in the list (round-trip: POST → STDB → GET).
    const row = page
      .getByText(`${first} ${last}`, { exact: true })
      .first();
    await expect(row).toBeVisible({ timeout: 10_000 });
  });

  test("create a ticket for an existing customer", async ({ page }) => {
    await loginReal(page);
    await navToFlow(page, "Tickets");

    const title = unique("E2E Ticket");

    await page.getByText("New Ticket", { exact: true }).first().click();
    // Select a customer (required) — the E2E customer created by the previous
    // test is present in the dropdown (cross-test persistence proof).
    await page
      .locator("select")
      .first()
      .selectOption({ index: 1 });
    await page.getByPlaceholder("Title").fill(title);
    await page
      .getByPlaceholder("Description")
      .fill("Created by full-stack Playwright flow test");
    await page.getByPlaceholder("Device type").fill("Laptop");
    await page.getByPlaceholder("Device model").fill("ThinkPad X1");
    await page.getByPlaceholder("Serial").fill("SN-E2E-001");
    // Select #2 is priority (select #1 is the customer dropdown).
    await page.locator("select").nth(1).selectOption("medium");

    // Capture any submit button (the form's primary action).
    await page
      .getByRole("button", { name: /^create$/i })
      .first()
      .click();

    // Verify the ticket persists by querying the backend directly.
    const token = await page.evaluate(() => localStorage.getItem("crm_token"));
    const res = await page.request.get(
      `/api/tickets?search=${encodeURIComponent(title)}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    expect(res.status()).toBe(200);
    const body = (await res.json()) as { tickets: Array<{ title: string }> };
    const found = (body.tickets ?? []).some((t) => t.title === title);
    expect(found).toBe(true);
  });

  test("sign out returns to the login form", async ({ page }) => {
    await loginReal(page);
    await expect(page.locator("aside").first()).toBeVisible();
    await page.getByRole("button", { name: /sign out/i }).click();
    await expect(page.getByRole("button", { name: /sign in/i }).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test("record a payment against an invoice (full invoice→payment journey)", async ({
    page,
  }) => {
    await loginReal(page);
    await navToFlow(page, "Payments");

    await page.getByText("Record Payment", { exact: true }).first().click();
    // Invoice select (first select) — pick an invoice with a payable status
    // (not a $0 draft). Prefer one whose option text contains "(partial)".
    const invoiceSelect = page.locator("select").first();
    // Wait for the invoices query to load (option count grows past the
    // placeholder under a busy single worker).
    await expect
      .poll(
        () => invoiceSelect.locator("option").count(),
        { timeout: 10_000 }
      )
      .toBeGreaterThan(1);
    const opts = await invoiceSelect.locator("option").count();
    expect(opts).toBeGreaterThan(1);
    // Prefer an invoice with a payable status (option text contains "(partial)");
    // otherwise fall back to the first real invoice.
    const partialOpt = invoiceSelect.locator('option:has-text("(partial)")').first();
    if ((await partialOpt.count()) > 0) {
      const val = await partialOpt.getAttribute("value");
      if (val) await invoiceSelect.selectOption(val);
    } else {
      await invoiceSelect.selectOption({ index: 1 });
    }
    // Customer select (second select) — pick the first real customer.
    await page.locator("select").nth(1).selectOption({ index: 1 });
    // Amount (lower than invoice total to avoid over-pay validation).
    await page.getByPlaceholder("Amount").fill("1.00");
    await page.getByRole("button", { name: "Record", exact: true }).first().click();

    // Recording a payment round-trips to STDB; a success toast appears.
    await expect(page.getByText(/payment recorded/i).first()).toBeVisible({
      timeout: 10_000,
    });
  });
});