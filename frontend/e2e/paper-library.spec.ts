import { expect, test } from "@playwright/test";

test("论文库使用真实接口呈现、筛选并打开添加入口", async ({ page }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await page.goto("/papers");

  await expect(page.getByRole("heading", { name: "论文库" })).toBeVisible();
  await expect(page.getByText(/\d+ 篇结果/)).toBeVisible();
  const list = page.getByLabel("论文工作列表，使用上下方向键选择，回车进入推荐工作");
  await expect(list).toBeVisible();
  await expect(list.getByRole("option")).toHaveCount(5);
  await list.press("ArrowDown");
  await expect(list.getByRole("option").nth(1)).toHaveAttribute("aria-current", "true");

  await page.getByLabel("论文筛选").getByLabel("未阅读").check();
  await expect(page).toHaveURL(/reading_status=unread/);

  await page.getByRole("button", { name: /添加论文/ }).click();
  await page.getByRole("menuitem", { name: /导入新论文/ }).click();
  await expect(page.getByRole("dialog", { name: "导入新论文" })).toBeVisible();
  await expect(page.getByLabel("DOI")).toBeFocused();
  await expect(page.getByRole("dialog", { name: "导入新论文" }).getByRole("button", { name: "添加论文", exact: true })).toBeDisabled();
});

test("小屏将筛选与概览切换为可关闭抽屉", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/papers");

  await page.getByRole("button", { name: "筛选" }).first().click();
  await expect(page.getByLabel("论文筛选")).toBeVisible();
  await page.getByRole("button", { name: "关闭筛选" }).click();

  await page.getByLabel("论文工作列表，使用上下方向键选择，回车进入推荐工作").getByRole("option").first().click();
  await expect(page.getByRole("complementary", { name: "论文概览" })).toBeVisible();
  await page.getByRole("button", { name: "关闭论文概览" }).click();
});
