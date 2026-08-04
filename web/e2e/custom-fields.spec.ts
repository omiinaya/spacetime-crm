import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navToSettingsTab } from "./helpers";

test.describe("Custom Fields (Settings → Data)", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navToSettingsTab(page, "Data & Fields");
  });

  test("page heading is visible", async ({ page }) => {
    const main = page.locator("main");
    await expect(main.getByText("Custom Fields", { exact: true }).first()).toBeVisible();
  });

  test("entity filter buttons render", async ({ page }) => {
    for (const name of ["All", "Customers", "Tickets", "Invoices", "Products"]) {
      const btn = page.getByRole("button", { name, exact: true }).first();
      await expect(btn).toBeVisible({ timeout: 5_000 });
    }
  });

  test("'Add Field' opens the creation form", async ({ page }) => {
    const addBtn = page.getByRole("button", { name: "Add Field" }).first();
    await expect(addBtn).toBeVisible();
    await addBtn.click();
    await waitForLoad(page);
    await expect(
      page.getByRole("button", { name: "Cancel", exact: true }).first()
    ).toBeVisible();
  });
});