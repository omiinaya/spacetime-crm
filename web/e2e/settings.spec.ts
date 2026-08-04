import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navTo } from "./helpers";

test.describe("Settings", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navTo(page, "Settings");
  });

  test("page heading and tab bar are visible", async ({ page }) => {
    await expect(page.locator("h1").first()).toContainText("Settings");
    for (const tab of ["General", "Notifications", "Business", "Data & Fields", "System"]) {
      await expect(page.getByRole("tab", { name: tab, exact: true })).toBeVisible();
    }
  });

  test("General tab shows user, preference, PIN and 2FA sections", async ({ page }) => {
    for (const s of [/users/i, /preferences/i, /pin/i, /two-factor|2fa/i]) {
      await expect(page.locator("main").getByText(s).first()).toBeVisible({ timeout: 5_000 });
    }
  });

  test("Notifications tab shows mail, SMS, reminder and webhook sections", async ({ page }) => {
    await page.getByRole("tab", { name: "Notifications" }).click();
    await waitForLoad(page);
    for (const s of [/smtp|mail/i, /sms/i, /reminder/i, /webhook/i]) {
      await expect(page.locator("main").getByText(s).first()).toBeVisible({ timeout: 5_000 });
    }
  });

  test("Business tab shows hours, taxes, SLA and revenue target", async ({ page }) => {
    await page.getByRole("tab", { name: "Business" }).click();
    await waitForLoad(page);
    for (const s of [/business hours/i, /tax/i, /sla/i, /revenue target/i]) {
      await expect(page.locator("main").getByText(s).first()).toBeVisible({ timeout: 5_000 });
    }
  });

  test("Data & Fields tab shows import/export, custom fields and audit log", async ({ page }) => {
    await page.getByRole("tab", { name: "Data & Fields" }).click();
    await waitForLoad(page);
    const main = page.locator("main");
    await expect(main.getByText(/import/i).first()).toBeVisible({ timeout: 5_000 });
    await expect(main.getByText("Custom Fields", { exact: true }).first()).toBeVisible();
    await expect(main.getByText(/audit/i).first()).toBeVisible();
  });

  test("System tab shows health, checklists, tenants and agent access", async ({ page }) => {
    await page.getByRole("tab", { name: "System" }).click();
    await waitForLoad(page);
    const main = page.locator("main");
    await expect(main.getByText(/health/i).first()).toBeVisible({ timeout: 5_000 });
    await expect(main.getByText("Tenants", { exact: true }).first()).toBeVisible();
    await expect(main.getByText(/agent access/i).first()).toBeVisible();
  });

  test("2FA section shows setup control", async ({ page }) => {
    await page.getByRole("tab", { name: "General" }).click();
    await waitForLoad(page);
    const section = page.locator("main").getByText(/two-factor/i).first();
    await expect(section).toBeVisible();
    const setup = page.getByRole("button", { name: /set up 2fa|enable|setup/i }).first();
    await expect(
      setup.or(page.getByRole("button", { name: /disable/i }).first())
    ).toBeVisible();
  });

  test("POS PIN section renders", async ({ page }) => {
    await expect(page.getByText("POS PIN Login").first()).toBeVisible();
    await expect(page.getByPlaceholder("Enter PIN").first()).toBeVisible();
  });
});