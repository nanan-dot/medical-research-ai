import { expect, test } from "@playwright/test";

for (const viewport of [
  { name: "1280x800", width: 1280, height: 800 },
  { name: "1440x900", width: 1440, height: 900 },
  { name: "1536x1024", width: 1536, height: 1024 },
  { name: "1024x768", width: 1024, height: 768 },
  { name: "768x1024", width: 768, height: 1024 },
]) {
  test(`论文研究入口在 ${viewport.name} 保持可用`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/paper-research");
    await expect(page.getByText("请选择一篇论文", { exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "返回论文库" })).toBeVisible();
    await page.screenshot({ path: `../docs/frontend-rebuild/screenshots/FE-R2/paper-reader-entry-${viewport.name}.png`, fullPage: true });
  });
}
