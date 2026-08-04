import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navTo } from "./helpers";

test.describe("Point of Sale", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navTo(page, "POS");
  });

  test("POS terminal renders", async ({ page }) => {
    await expect(page.locator("main")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /scan or search products/i }).first()
    ).toBeVisible();
  });

  test("product search input accepts text", async ({ page }) => {
    const input = page.getByPlaceholder("Scan barcode or search products...").first();
    await expect(input).toBeVisible();
    await input.fill("Cable");
    await expect(input).toHaveValue("Cable");
  });

  test("sale details panel renders", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Sale Details" }).first()).toBeVisible();
    for (const label of ["Cash", "Card", "Gift"]) {
      await expect(page.getByRole("button", { name: label, exact: true }).first()).toBeVisible();
    }
  });

  test("lock POS terminal control is present", async ({ page }) => {
    await expect(page.getByRole("button", { name: /lock pos terminal/i }).first()).toBeVisible();
  });
});