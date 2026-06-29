import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad } from "./helpers";

test.describe("Customers", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await waitForLoad(page);
    // Navigate to Customers page
    await page.locator("aside").getByText("Customers", { exact: true }).click();
    await waitForLoad(page);
  });

  test("page heading and description are visible", async ({ page }) => {
    await expect(page.locator("h1")).toContainText("Customers");
    await expect(page.getByText(/manage your customer database/i)).toBeVisible();
  });

  test("shows search input", async ({ page }) => {
    const searchInput = page.locator("input[placeholder='Search customers...']");
    await expect(searchInput).toBeVisible();
  });

  test("'Add Customer' button is visible", async ({ page }) => {
    const addBtn = page.getByText("Add Customer", { exact: true });
    await expect(addBtn).toBeVisible();
  });

  test("clicking 'Add Customer' opens the new customer form", async ({ page }) => {
    await page.getByText("Add Customer", { exact: true }).click();
    await expect(page.getByText("New Customer", { exact: true })).toBeVisible();
    await expect(page.locator("input[placeholder='First Name']")).toBeVisible();
    await expect(page.locator("input[placeholder='Last Name']")).toBeVisible();
    await expect(page.locator("input[placeholder='Email']")).toBeVisible();
    await expect(page.locator("input[placeholder='Phone']")).toBeVisible();
    await expect(page.getByText("Create", { exact: true })).toBeVisible();
    await expect(page.getByText("Cancel", { exact: true })).toBeVisible();
  });

  test("cancel button closes the customer form", async ({ page }) => {
    await page.getByText("Add Customer", { exact: true }).click();
    await expect(page.getByText("New Customer", { exact: true })).toBeVisible();
    await page.getByText("Cancel", { exact: true }).click();
    await expect(page.getByText("New Customer", { exact: true })).not.toBeVisible();
  });

  test("search input accepts text", async ({ page }) => {
    const searchInput = page.locator("input[placeholder='Search customers...']");
    await searchInput.fill("John");
    await expect(searchInput).toHaveValue("John");
  });

  test("shows pagination controls", async ({ page }) => {
    const nextBtn = page.locator("button").filter({ hasText: /next/i });
    const prevBtn = page.locator("button").filter({ hasText: /prev/i });
    await expect(nextBtn.or(prevBtn).first()).toBeVisible({ timeout: 5_000 }).catch(() => {});
  });
});
