import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navTo } from "./helpers";

test.describe("Appointments", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navTo(page, "Appointments");
  });

  test("page heading is visible", async ({ page }) => {
    await expect(page.locator("h1").first()).toContainText("Appointments");
  });

  test("'New Appointment' button is visible", async ({ page }) => {
    const btn = page.getByRole("button", { name: "New Appointment" }).first();
    await expect(btn).toBeVisible();
  });

  test("new appointment form opens and cancels", async ({ page }) => {
    const btn = page.getByRole("button", { name: "New Appointment" }).first();
    await btn.click();
    await waitForLoad(page);
    const cancel = page.getByRole("button", { name: "Cancel", exact: true }).first();
    await expect(cancel).toBeVisible();
    await cancel.click();
    await expect(btn).toBeVisible();
  });
});