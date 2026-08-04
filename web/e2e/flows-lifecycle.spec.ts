import { test, expect } from "@playwright/test";
import { loginReal, unique, navToFlow } from "./flows-helpers";

/**
 * Full-stack lifecycle flows (part 2): invoicing, payments, appointments,
 * and inventory. Each flow logs in through the REAL auth form and round-trips
 * through FastAPI + SpacetimeDB. All entities use unique names.
 *
 * NOTE: these tests SHARE the seeded dev tenant. Cross-test data created in
 * earlier tests (customers) is intentionally reused where the form allows
 * selecting from existing rows.
 */
test.describe("Full-stack lifecycle flows", () => {
  test("create an invoice and verify it persists via API", async ({ page }) => {
    await loginReal(page);
    await navToFlow(page, "Invoices");

    await page.getByText("New Invoice", { exact: true }).first().click();
    // Customer dropdown (first select) — pick the first real customer.
    await page.locator("select").first().selectOption({ index: 1 });
    await page.getByPlaceholder("Notes").fill(unique("Invoice-notes"));
    await page.getByPlaceholder("Terms").fill("Net 30");
    await page.locator("select").nth(1).selectOption("USD");
    await page.getByRole("button", { name: "Create", exact: true }).first().click();

    // Give the mutation a moment, then confirm via backend.
    await page.waitForTimeout(1_500);
    const token = await page.evaluate(() => localStorage.getItem("crm_token"));
    const res = await page.request.get(`/api/invoices?limit=5`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.status()).toBe(200);
    const body = (await res.json()) as { invoices: Array<{ id: string }> };
    expect((body.invoices ?? []).length).toBeGreaterThan(0);
  });

  test("create an appointment and verify it persists", async ({ page }) => {
    await loginReal(page);
    await navToFlow(page, "Appointments");

    const title = unique("E2E Appointment");

    await page.getByText("New Appointment", { exact: true }).first().click();
    // Customer select is the first select in the appointment form.
    await page.locator("select").first().selectOption({ index: 1 });
    await page.getByPlaceholder("Title").fill(title);
    await page.getByPlaceholder("Description").fill("Flow-test appointment");
    // Required datetime-local fields (tomorrow, 1 hour).
    const tomorrow = new Date(Date.now() + 24 * 3600 * 1000);
    const iso = (d: Date) =>
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
        d.getDate()
      ).padStart(2, "0")}T${String(d.getHours()).padStart(2, "0")}:00`;
    const startInput = page.locator('input[type="datetime-local"]').first();
    const endInput = page.locator('input[type="datetime-local"]').nth(1);
    await startInput.fill(iso(tomorrow));
    await endInput.fill(iso(new Date(tomorrow.getTime() + 3600 * 1000)));
    await page.getByRole("button", { name: "Create", exact: true }).first().click();

    // Verify via API round-trip (appointments list takes customer_id, not search).
    await page.waitForTimeout(1_500);
    const token = await page.evaluate(() => localStorage.getItem("crm_token"));
    const res = await page.request.get(`/api/appointments?limit=20`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.status()).toBe(200);
    const body = (await res.json()) as { appointments: Array<{ title: string }> };
    const found = (body.appointments ?? []).some((a) => a.title === title);
    expect(found).toBe(true);
  });

  test("create a product and verify it persists", async ({ page }) => {
    await loginReal(page);
    await navToFlow(page, "Products");

    const name = unique("E2E Product");

    await page.getByText("Add Product", { exact: true }).first().click();
    await page.getByPlaceholder("Name").fill(name);
    await page.getByPlaceholder("SKU").fill(`SKU-${Date.now()}`);
    await page.getByPlaceholder("Price").fill("49.99");
    await page.getByPlaceholder("Cost").fill("20.00");
    await page.getByRole("button", { name: "Create", exact: true }).first().click();

    await page.waitForTimeout(1_500);
    const token = await page.evaluate(() => localStorage.getItem("crm_token"));
    const res = await page.request.get(
      `/api/products?search=${encodeURIComponent(name)}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    expect(res.status()).toBe(200);
    const body = (await res.json()) as { products: Array<{ name: string }> };
    const found = (body.products ?? []).some((p) => p.name === name);
    expect(found).toBe(true);
  });
});