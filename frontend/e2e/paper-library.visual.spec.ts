import { expect, test } from "@playwright/test";

const outputDirectory = "../docs/frontend/paper-library-v31";
const viewports = [
  { name: "actual-1536x1024.png", width: 1536, height: 1024 },
  { name: "actual-1280x900.png", width: 1280, height: 900 },
  { name: "actual-1024x768.png", width: 1024, height: 768 },
  { name: "actual-768x1024.png", width: 768, height: 1024 },
  { name: "actual-390x844.png", width: 390, height: 844 },
] as const;

for (const viewport of viewports) {
  test(`论文库视觉验收 ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("/papers");
    await expect(page.getByRole("heading", { name: "论文库" })).toBeVisible();
    await expect(page.getByLabel("论文工作列表，使用上下方向键选择，回车进入推荐工作")).toBeVisible();
    await page.screenshot({ path: `${outputDirectory}/${viewport.name}` });
  });
}
