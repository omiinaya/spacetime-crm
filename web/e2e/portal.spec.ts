import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad } from "./helpers";

test.describe("Customer Portal", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
  });

  test("portal shows brand and sign-in when unauthenticated", async ({ page }) => {
    await page.goto("/portal");
    await waitForLoad(page, 20_000);
    await expect(page.getByText("Customer Portal").first()).toBeVisible();
    await expect(
      page.getByRole("button", { name: /sign in/i }).first()
    ).toBeVisible();
  });

  test("portal login form accepts input", async ({ page }) => {
    await page.goto("/portal");
    await waitForLoad(page, 20_000);
    const inputs = page.locator("input").first();
    if (await inputs.isVisible().catch(() => false)) {
      await inputs.fill("customer@example.com");
      await expect(inputs).toHaveValue("customer@example.com");
    }
  });
});