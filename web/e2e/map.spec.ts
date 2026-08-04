import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navToSubTab } from "./helpers";

test.describe("Map", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navToSubTab(page, "Customers", "Map");
  });

  test("map page renders without errors", async ({ page }) => {
    await expect(page.locator("main")).toBeVisible();
    const body = page.locator("body");
    await expect(body).not.toContainText("Application Error", { useInnerText: true });
  });

  test("customer map summary renders", async ({ page }) => {
    // The map page shows customers with and without locations
    await expect(page.locator("main").getByText(/customer map/i).first()).toBeVisible();
  });
});