import { expect, test } from "@playwright/test";

const paperItemId = process.env.PAPER_READER_E2E_ITEM_ID ?? "6";

for (const viewport of [
  { name: "1280x800", width: 1280, height: 800 },
  { name: "1440x900", width: 1440, height: 900 },
  { name: "1536x1024", width: 1536, height: 1024 },
  { name: "1024x768", width: 1024, height: 768 },
  { name: "768x1024", width: 768, height: 1024 },
]) {
  test(`真实论文阅读工作区在 ${viewport.name} 可用`, async ({ page }) => {
    await page.setViewportSize({
      width: viewport.width,
      height: viewport.height,
    });
    const bootstrap = page.waitForResponse(
      (response) =>
        response
          .url()
          .includes(`/paper-reader/items/${paperItemId}/bootstrap`) &&
        response.ok(),
    );
    await page.goto(`/paper-research/${paperItemId}`);
    await bootstrap;
    await expect(
      page.getByRole("heading", {
        name: /ERS\/EULAR clinical practice guidelines/,
      }),
    ).toBeVisible();
    if (viewport.width < 1024) {
      await page.getByRole("button", { name: "阅读导航", exact: true }).click();
      await expect(page.getByLabel("阅读导航", { exact: true })).toBeVisible();
      await page.getByRole("button", { name: "阅读导航", exact: true }).click();
    } else {
      await expect(page.getByLabel("阅读导航", { exact: true })).toBeVisible();
    }
    await expect(page.getByLabel("我的记录与 SW Copilot")).toBeVisible();
    await expect(page.getByRole("tab", { name: "实时翻译" })).toBeVisible();
    await page.getByRole("tab", { name: "实时翻译" }).click();
    await expect(page.getByText("翻译服务未启用")).toHaveCount(0);
    await expect(page.getByRole("tab", { name: "双语" })).toBeEnabled();
    await expect(page.getByRole("tab", { name: "中文" })).toBeEnabled();
    await page.getByRole("tab", { name: "SW Copilot" }).click();
    await expect(
      page.getByRole("heading", { name: "AI阅读助手" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /解释当前段落/ }),
    ).toBeVisible();
    await page.getByRole("button", { name: /总结本章节/ }).click();
    await expect(page.getByPlaceholder("基于当前论文提问…")).toHaveValue(
      "请总结当前章节的研究内容和关键结论。",
    );
    await expect(page.locator(".pdf-page").first()).toBeVisible({
      timeout: 20_000,
    });
    await expect(
      page.getByRole("navigation", { name: "页面缩略图" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "转到第 1 页" }),
    ).toBeVisible();
    await page.screenshot({
      path: `../docs/frontend-rebuild/screenshots/FE-R2/paper-reader-real-${viewport.name}.png`,
      fullPage: true,
    });
  });
}

test("真实工作区可通过工具栏翻页", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/paper-research/${paperItemId}`);
  await expect(page.locator(".pdf-page[data-page-number='1']")).toBeVisible({
    timeout: 20_000,
  });
  await page.getByRole("button", { name: "下一页" }).click();
  await expect(page.locator(".pdf-page[data-page-number='2']")).toBeVisible({
    timeout: 10_000,
  });
});

test("阅读工具栏的双语与中文模式会替换中央阅读内容", async ({ page }) => {
  test.setTimeout(90_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/paper-research/${paperItemId}`);
  const modes = page.getByRole("tablist", { name: "阅读模式" });
  await expect(modes.getByRole("tab", { name: "双语" })).toBeEnabled();

  await modes.getByRole("tab", { name: "双语" }).click();
  const translatedCanvas = page.getByLabel("论文译文阅读");
  await expect(translatedCanvas).toBeVisible({ timeout: 30_000 });
  await expect(translatedCanvas.locator(".translated-segment").first()).toBeVisible({
    timeout: 30_000,
  });
  await expect(translatedCanvas.locator(".source-text").first()).toBeVisible();

  const returnToSource = translatedCanvas.getByRole("button", { name: "回到原文" }).first();
  await expect(returnToSource).toBeVisible({ timeout: 30_000 });
  await returnToSource.click();
  await expect(modes.getByRole("tab", { name: "原文" })).toHaveAttribute("aria-selected", "true");
  await expect(page.locator(".pdf-page").first()).toBeVisible({ timeout: 20_000 });

  await modes.getByRole("tab", { name: "双语" }).click();
  await expect(translatedCanvas).toBeVisible();

  await modes.getByRole("tab", { name: "中文" }).click();
  await expect(translatedCanvas).toBeVisible();
  await expect(
    translatedCanvas.locator(
      ".translated-segment:not([data-quality='blocked']) .source-text",
    ),
  ).toHaveCount(0);

  await modes.getByRole("tab", { name: "原文" }).click();
  await expect(page.locator(".pdf-page").first()).toBeVisible({ timeout: 20_000 });
});

test("左侧导航可切换搜索且收起后扩展右侧记录区", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/paper-research/${paperItemId}`);
  await expect(page.locator(".pdf-page").first()).toBeVisible({
    timeout: 20_000,
  });
  await page.getByRole("tab", { name: "阅读历史" }).click();
  await expect(page.getByText("当前阅读位置", { exact: true })).toBeVisible();
  await page.getByPlaceholder("搜索阅读历史").fill("不存在");
  await expect(
    page.getByText("没有匹配的阅读记录。", { exact: true }),
  ).toBeVisible();
  const context = page.getByLabel("我的记录与 SW Copilot");
  const before = await context.boundingBox();
  await page.getByRole("button", { name: "收起阅读导航" }).click();
  const after = await context.boundingBox();
  expect(after!.width).toBeGreaterThan(before!.width + 150);
});

test("原文选区可打开笔记编辑器", async ({ page }) => {
  test.setTimeout(90_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const bootstrapResponse = page.waitForResponse(
    (response) =>
      response.url().includes(`/paper-reader/items/${paperItemId}/bootstrap`) &&
      response.ok(),
  );
  await page.goto(`/paper-research/${paperItemId}`);
  const bootstrap = await (await bootstrapResponse).json();
  const text = page
    .locator(".pdf-page[data-page-number='1'] .text-layer span")
    .filter({ hasText: /\S/ })
    .first();
  await expect(text).toBeVisible({ timeout: 20_000 });
  await expect(text).toHaveAttribute("data-anchor-revision-id", /\d+/, {
    timeout: 20_000,
  });
  await text.selectText();
  await page.locator(".pdf-pages").dispatchEvent("mouseup");
  await page.getByRole("button", { name: "笔记", exact: true }).click();
  await expect(page.getByLabel("为选中的原文添加笔记")).toBeVisible();
  await page.getByLabel("为选中的原文添加笔记").fill("Playwright 选区笔记验收");
  const createdResponse = page.waitForResponse(
    (response) =>
      response
        .url()
        .includes(`/documents/${bootstrap.paper.document_id}/annotations`) &&
      response.request().method() === "POST" &&
      response.ok(),
  );
  await page.getByRole("button", { name: "保存笔记" }).click();
  const created = await (await createdResponse).json();
  await expect(page.getByLabel("为选中的原文添加笔记")).toBeHidden();
  const cleanup = await page.request.delete(
    `http://127.0.0.1:8000/api/v1/documents/${bootstrap.paper.document_id}/annotations/${created.id}?expected_file_hash=${encodeURIComponent(bootstrap.document.file_hash)}`,
  );
  expect(cleanup.ok()).toBeTruthy();
});

test("单行选区冻结为精确覆盖层且保留操作工具栏", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/paper-research/${paperItemId}`);
  const text = page
    .locator(".pdf-page[data-page-number='1'] .text-layer span")
    .filter({ hasText: /[A-Za-z]{4,}/ })
    .first();
  await expect(text).toBeVisible({ timeout: 20_000 });
  await expect(text).toHaveAttribute("data-anchor-revision-id", /\d+/, {
    timeout: 20_000,
  });
  await text.selectText();
  await page.locator(".pdf-pages").dispatchEvent("mouseup");

  await expect(page.locator(".selection-highlight").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "翻译", exact: true })).toBeVisible();
  expect(await page.evaluate(() => window.getSelection()?.toString() ?? "")).toBe("");
});

test("选区可由本地翻译 Worker 生成受质量门禁保护的译文", async ({ page }) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/paper-research/${paperItemId}`);
  const text = page
    .locator(".pdf-page[data-page-number='1'] .text-layer span")
    .filter({ hasText: /[A-Za-z]{4,}/ })
    .first();
  await expect(text).toBeVisible({ timeout: 20_000 });
  await expect(text).toHaveAttribute("data-anchor-revision-id", /\d+/, {
    timeout: 20_000,
  });
  await text.selectText();
  await page.locator(".pdf-pages").dispatchEvent("mouseup");
  await page.getByRole("button", { name: "翻译", exact: true }).click();
  await expect(page.getByRole("heading", { name: "医学选区翻译" })).toBeVisible();
  await page.getByRole("button", { name: "翻译此选区" }).click();
  await expect(page.locator(".translation-panel [role='status']")).toContainText("翻译处理完成", {
    timeout: 120_000,
  });
  await expect(page.getByLabel("翻译结果")).toBeVisible();
  await expect(page.getByText("机器核对不等于医学专家审核。请结合原文和专业判断使用。")).toBeVisible();
});

test("我的记录可在独立弹层中筛选并截图", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/paper-research/${paperItemId}`);
  await expect(page.getByLabel("我的记录与 SW Copilot")).toBeVisible();
  await page.getByRole("button", { name: /全部记录/ }).click();
  await expect(page.getByRole("dialog", { name: "我的记录" })).toBeVisible();
  await page.screenshot({ path: "../docs/frontend-rebuild/screenshots/FE-R2/paper-reader-records-modal-1440x900.png", fullPage: true });
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "我的记录" })).toBeHidden();
});
