import { expect, test } from "@playwright/test";

test("stable A4 segment submits one real anchored follow intent without replacing the PDF", async ({ page }) => {
  await page.goto("/documents/1");
  await expect(page.locator('.pdf-page[data-page-number="1"] .text-layer')).toBeVisible();
  const intentPromise = page.waitForResponse(response =>
    response.url().endsWith("/translation-segment-intents") && response.request().method() === "POST",
  );
  await page.getByRole("tab", { name: "翻译", exact: true }).click();
  const intent = await intentPromise;
  expect(intent.status()).toBe(202);
  const payload = intent.request().postDataJSON() as { segment_ids: number[]; active_segment_id: number | null; trigger: string };
  expect(payload.trigger).toBe("follow");
  expect(payload.active_segment_id).not.toBeNull();
  expect(payload.segment_ids).toContain(payload.active_segment_id!);
  await expect(page.locator(".pdf-reader")).toBeVisible();
  await expect(page.getByText("正在翻译当前稳定段落")).toBeVisible();
});
