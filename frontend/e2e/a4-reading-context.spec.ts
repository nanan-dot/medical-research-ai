import { expect, test } from "@playwright/test";

test("real A0/A1 reader publishes visible segments and rejects a mismatched revision", async ({ page }) => {
  await page.goto("/documents/1");
  await expect(page.getByRole("status").filter({ hasText: "当前段落 #" })).toBeVisible();
  await page.route("**/source-segments?*", async route => {
    const response = await route.fetch();
    const payload = await response.json();
    await route.fulfill({ json: { ...payload, segmentation_revision_id: 999999 } });
  });
  await page.reload();
  await expect(page.getByRole("alert").filter({ hasText: "可视段落版本不一致" })).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "当前段落 #" })).toHaveCount(0);
});
