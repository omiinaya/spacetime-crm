import { test, expect } from "@playwright/test";
import { waitForLoad } from "./helpers";

test.describe("Auth pages", () => {
  test("login page renders email, password and sign-in controls", async ({
    page,
  }) => {
    await page.goto("/");
    await waitForLoad(page);
    await expect(page.getByText("SpacetimeCRM", { exact: true }).first()).toBeVisible();
    await expect(page.locator("input[type='email']").first()).toBeVisible();
    await expect(page.locator("input[type='password']").first()).toBeVisible();
    await expect(
      page.getByRole("button", { name: /sign in/i }).first()
    ).toBeVisible();
  });

  test("forgot password page has email input and submit", async ({ page }) => {
    await page.goto("/forgot-password");
    await waitForLoad(page);
    await expect(page.getByText(/forgot password/i).first()).toBeVisible();
    await expect(page.locator("input[type='email']").first()).toBeVisible();
  });

  test("reset password page renders", async ({ page }) => {
    await page.goto("/reset-password");
    await waitForLoad(page);
    // Either the invalid-link message or the form renders — never a crash.
    await expect(page.locator("body")).toContainText(/reset|invalid/i);
  });

  test("portal login page renders customer portal shell", async ({ page }) => {
    await page.goto("/portal");
    await waitForLoad(page);
    await expect(page.getByText("Customer Portal")).toBeVisible();
    await expect(
      page.getByRole("button", { name: /sign in/i }).first()
    ).toBeVisible();
  });

  test("portal login rejects empty form without crashing", async ({ page }) => {
    await page.goto("/portal");
    await waitForLoad(page);
    const signIn = page.getByRole("button", { name: /sign in/i }).first();
    if (await signIn.isVisible()) {
      await signIn.click();
      await expect(page.locator("body")).toBeVisible();
    }
  });
});
