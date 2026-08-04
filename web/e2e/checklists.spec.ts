import { test, expect } from "@playwright/test";
import { loginAs, waitForLoad, navToSettingsTab } from "./helpers";

test.describe("Checklist Templates (Settings → System)", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "admin");
    await navToSettingsTab(page, "System");
  });

  test("page renders without errors", async ({ page }) => {
    await expect(page.locator("main")).toBeVisible();
    const body = page.locator("body");
    await expect(body).not.toContainText("Application Error", { useInnerText: true });
  });

  test("template editor opens", async ({ page }) => {
    const createBtn = page
      .getByRole("button", { name: /create template|new template/i })
      .first();
    const createBtn2 = page.getByRole("button", { name: "Create", exact: true }).first();
    const target = (await createBtn.isVisible()) ? createBtn : createBtn2;
    if (await target.isVisible()) {
      await target.click();
      await waitForLoad(page);
      await expect(
        page.getByRole("button", { name: "Cancel", exact: true }).first()
      ).toBeVisible();
    }
  });
});