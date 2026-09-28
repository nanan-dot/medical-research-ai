import { expect, test } from "@playwright/test";

test("empty scope, keyboard send, source identity and saved history", async ({ page }) => {
  await page.goto("/research-chat");
  await expect(page.getByRole("heading", { name: "研究问题，不必从上传开始" })).toBeVisible();
  await page.getByLabel("你的问题").fill("你好");
  await expect(page.getByRole("button", { name: "发送问题" })).toBeEnabled();
  await page.getByLabel("你的问题").press("Control+Enter");
  await expect(page.getByText("验收替身：通用回答。未调用真实模型。", { exact: true })).toBeVisible();
  await expect(page.locator(".chat-message")).toHaveCount(2);
  await expect(page.locator(".chat-message details")).toHaveCount(0);
  const selected = await page.getByLabel("历史对话").inputValue();
  await page.reload();
  await page.getByLabel("历史对话").selectOption(selected);
  await expect(page.locator(".chat-message")).toHaveCount(2);
  await expect(page.locator(".chat-message").last()).toContainText("模型通用回答");
  await page.screenshot({ path: "test-results/research-chat/desktop.png", fullPage: true });
});

test("paper sections, scoped citation and mixed shortage gap deletion", async ({ page }) => {
  await page.goto("/research-chat");
  await page.getByRole("checkbox", { name: /文献 1|paper.txt/ }).check();
  await page.getByLabel("你的问题").fill("这篇论文的结论");
  await page.getByRole("button", { name: "发送问题" }).click();
  await expect(page.locator(".answer-section[data-source=paper_grounded]")).toBeVisible();
  await page.locator("summary").first().click();
  await expect(page.getByRole("link", { name: "打开资料详情核对原文" })).toHaveAttribute("href", "/documents/1");
  await page.getByLabel("证据不足时补充通用解释").check();
  await page.getByLabel("你的问题").fill("这篇论文证据不足时怎么理解");
  await page.getByRole("button", { name: "发送问题" }).click();
  const last = page.locator(".chat-message").last();
  await expect(last.locator("[data-source=general]")).toBeVisible();
  await expect(last.locator("[data-source=general] details")).toHaveCount(0);
  const remove = page.getByRole("button", { name: "删除知识缺口：这篇论文证据不足时怎么理解" });
  await expect(remove).toBeVisible();
  await remove.click();
  await expect(remove).toHaveCount(0);
});

test("web opt-in is separate, failure visible, cancel leaves no successful duplicate", async ({ page }) => {
  await page.goto("/research-chat");
  await page.getByLabel("你的问题").fill("最新指南");
  await page.getByRole("button", { name: "发送问题" }).click();
  await expect(page.getByText("尚未允许外部检索", { exact: true })).toBeVisible();
  await page.getByLabel("允许 PubMed 外部检索").check();
  await page.getByLabel("发送给 PubMed 的公开检索词").fill("public-test-query");
  await page.getByRole("button", { name: "发送问题" }).click();
  await expect(page.getByText("验收替身：外部检索词 public-test-query", { exact: true })).toBeVisible();
  await page.getByLabel("回答模式").selectOption("general");
  await page.getByLabel("你的问题").fill("服务故障");
  await page.getByRole("button", { name: "发送问题" }).click();
  await expect(page.getByText("模型生成失败，请检查模型设置", { exact: true })).toBeVisible();
  await page.getByLabel("你的问题").fill("您好");
  await page.getByRole("button", { name: "发送问题" }).click();
  await expect(page.getByRole("status").filter({ hasText: "正在回答" })).toBeVisible();
  await page.getByRole("button", { name: "取消回答" }).click();
  await expect(page.locator(".chat-message").last()).toContainText("已取消");
  await expect(page.locator(".chat-message")).toHaveCount(8);
});

test("mobile layout and keyboard focus", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/research-chat");
  await expect(page.getByLabel("你的问题")).toBeVisible();
  await expect(page.getByLabel("你的问题")).toBeEnabled();
  await page.getByLabel("你的问题").focus();
  await expect(page.getByLabel("你的问题")).toBeFocused();
  const overflow = await page.locator(".research-chat").evaluate(element => element.scrollWidth > element.clientWidth);
  expect(overflow).toBe(false);
  await page.screenshot({ path: "test-results/research-chat/mobile.png", fullPage: true });
});
