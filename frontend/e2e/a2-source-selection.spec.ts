import { test, expect } from "@playwright/test";

test("real PDF.js selection saves a shared anchor and restores exact highlight after reload", async ({ page }) => {
  await page.goto("/documents/1");
  const span = page.locator('.pdf-page[data-page-number="1"] [data-text-item-index="0"]');
  await expect(span).toBeVisible();
  const selectedText = (await span.textContent())?.trim();
  expect(selectedText).toBeTruthy();
  await expect(page.getByRole("status").filter({ hasText: "正在渲染" })).toHaveCount(0);
  await span.evaluate(element => {
    const range = document.createRange(); range.selectNodeContents(element);
    const selection = window.getSelection()!; selection.removeAllRanges(); selection.addRange(range);
    document.dispatchEvent(new Event("selectionchange"));
  });
  await expect(page.getByText("已记录选中文字，可在右侧批注中保存。")).toBeVisible();
  await page.getByRole("tab", { name: "批注", exact: true }).click();
  await page.getByRole("textbox", { name: "笔记内容" }).fill("A2 shared anchor note");
  const noteResponsePromise = page.waitForResponse(response => response.url().endsWith("/reading-notes") && response.request().method() === "POST");
  await page.getByRole("button", { name: "保存笔记", exact: true }).click();
  const note = await (await noteResponsePromise).json();
  await page.getByRole("textbox", { name: "备注（可选）" }).fill("A2 browser verification");
  const responsePromise = page.waitForResponse(response => response.url().endsWith("/annotations") && response.request().method() === "POST");
  await page.getByRole("button", { name: "保存批注", exact: true }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(201);
  const annotation = await response.json();
  expect(annotation.source_anchor_id).toBeGreaterThan(0);
  expect(note.source_anchor_id).toBe(annotation.source_anchor_id);
  expect(annotation.selected_text).toBe(selectedText);
  await page.reload();
  await expect(page.locator(`[data-annotation-id="${annotation.id}"]`).first()).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "按 TextItem 字符范围精确定位" })).toBeVisible();
  await page.getByRole("button", { name: "放大 PDF" }).click();
  await expect(page.getByRole("status").filter({ hasText: "正在渲染" })).toHaveCount(0);
  await expect(page.locator(`[data-annotation-id="${annotation.id}"]`).first()).toBeVisible();
  await page.screenshot({ path: "test-results/a2-selection-restored.png", fullPage: true });
});

test("ambiguous cross-page native selection is blocked without saving a false anchor", async ({ page }) => {
  await page.goto("/documents/1");
  const first = page.locator('.pdf-page[data-page-number="1"] [data-text-item-index="0"]');
  const second = page.locator('.pdf-page[data-page-number="2"] [data-text-item-index="0"]');
  await expect(first).toBeVisible();
  await expect(second).toBeVisible();
  await first.evaluate((start, end) => {
    const firstText = start.firstChild!;
    const lastText = end.firstChild!;
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.setBaseAndExtent(firstText, 0, lastText, lastText.textContent!.length);
    document.dispatchEvent(new Event("selectionchange"));
  }, await second.elementHandle());
  await expect(page.getByRole("alert")).toContainText("SELECTION_CROSSES_BLOCKED_REGION");
  await expect(page.getByText("已记录选中文字，可在右侧批注中保存。")).toHaveCount(0);
});
