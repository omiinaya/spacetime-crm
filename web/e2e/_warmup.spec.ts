import { test } from "@playwright/test";
import { loginAs, waitForLoad } from "./helpers";

/**
 * Vite cold-start warmup.
 *
 * Vite lazily transforms each page's module graph on first visit. Heavy pages
 * (Customers, Invoices, POS, Reports, ...) can take >60s to compile on a cold
 * dev server. This spec runs first (underscore sorts before letters) and
 * visits every heavy page — including sub-tabs and Settings tabs — so later
 * tests never hit a cold-compile timeout.
 */
const WARMUP_TIMEOUT = 300_000;

test.describe("warmup", () => {
  test("pre-compile all heavy pages", async ({ page }) => {
    test.setTimeout(WARMUP_TIMEOUT);
    await loginAs(page, "admin");
    await waitForLoad(page);

    const pages = [
      "Dashboard",
      "Customers",
      "Tickets",
      "Invoices",
      "Payments",
      "Estimates",
      "Appointments",
      "Products",
      "Purchase Orders",
      "POS",
      "Email Campaigns",
      "Reports",
      "Settings",
    ];

    for (const label of pages) {
      await page.locator("aside").getByText(label, { exact: true }).click();
      await page.waitForSelector("main", { state: "attached", timeout: WARMUP_TIMEOUT });
    }

    // Sub-tabs (consolidated pages)
    const subTabs: [string, string][] = [
      ["Customers", "Map"],
      ["Invoices", "Recurring"],
      ["Payments", "Payment Methods"],
      ["Payments", "Gift Cards"],
      ["Appointments", "Tech Schedule"],
    ];
    for (const [parent, sub] of subTabs) {
      await page.locator("aside").getByText(parent, { exact: true }).click();
      await page.waitForSelector("main", { state: "attached", timeout: WARMUP_TIMEOUT });
      await page.getByRole("tab", { name: sub, exact: true }).click();
      await page.waitForSelector("main", { state: "attached", timeout: WARMUP_TIMEOUT });
    }

    // Settings tabs
    await page.locator("aside").getByText("Settings", { exact: true }).click();
    await page.waitForSelector("main", { state: "attached", timeout: WARMUP_TIMEOUT });
    for (const tab of ["Notifications", "Business", "Data & Fields", "System"]) {
      await page.getByRole("tab", { name: tab, exact: true }).click();
      await page.waitForSelector("main", { state: "attached", timeout: WARMUP_TIMEOUT });
    }
  });
});
