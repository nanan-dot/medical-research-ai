import { test, expect } from "@playwright/test";

test("AC-PCF-12 论文中心闭环与 1774×887 视觉入口", async ({ page }) => {
  await page.route("**/api/v1/paper-research/center", async (route) => {
    await route.fulfill({ json: { current_research: { research_context_id: 7, research_name: "围术期镇痛证据", stage: "literature_reading", version: 2 }, continue_tasks: [{ paper_item_id: 42, title: "Perioperative pain evidence", journal: "Lancet", year: 2025, work_mode: "reading", current_section: "Methods", reading_progress_percent: 48, analysis_completed: 0, analysis_total: 0, last_work_at: "2026-09-01T00:00:00Z", entry_available: true, next_action: { kind: "continue_reading", title: "继续阅读", description: "从最近有效阅读位置继续", reason_codes: [], target: { item_id: 42, session_id: 9, page: 4, offset: 0.2 }, is_available: true, unavailable_reason: null }, sort_reason: "reading_incomplete" }], recent_activities: [], recent_papers: [], summary: { papers: 3, reading: 1, deep_reading: 1, completed: 1, pending_confirmation_items: 0, pending_confirmation_fields: 0 }, capabilities: { ai_task_planning: "unavailable" } } });
  });
  await page.setViewportSize({ width: 1774, height: 887 });
  await page.goto("/paper-center");
  await expect(page.getByRole("heading", { name: "论文中心" })).toBeVisible();
  await expect(page.getByTestId("continue-research")).toBeVisible();
  // AppShell 为路由切换保留了短暂的进入过渡；等页面稳定后再做视觉留档。
  await page.waitForTimeout(220);
  await page.screenshot({ path: "test-results/paper-center-1774x887.png", fullPage: true });
  await page.getByTestId("continue-action").click();
  // 目标参数的精确拼接由 composable 单测覆盖；这里确认主任务动作可操作且页面不崩溃。
  await expect(page.getByRole("heading", { name: "论文中心" })).toBeVisible();
});
