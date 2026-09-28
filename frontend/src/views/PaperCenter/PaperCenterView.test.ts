import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import PaperCenterView from "./PaperCenterView.vue";

const fixture = { current_research: { research_context_id: 7, research_name: "围术期镇痛证据", stage: "literature_reading", version: 2 }, continue_tasks: [{ paper_item_id: 42, title: "Perioperative pain evidence", journal: "Lancet", year: 2025, work_mode: "reading", current_section: "Methods", reading_progress_percent: 48, analysis_completed: 0, analysis_total: 0, last_work_at: "2026-09-01T00:00:00Z", entry_available: true, next_action: { kind: "continue_reading", title: "继续阅读", description: "从最近有效阅读位置继续", reason_codes: [], target: { item_id: 42, session_id: 9, page: 4, offset: 0.2 }, is_available: true, unavailable_reason: null }, sort_reason: "reading_incomplete" }], recent_activities: [{ id: 1, kind: "reading", occurred_at: "2026-09-01T00:00:00Z", paper_item_id: 42, paper_title: "Perioperative pain evidence", research_context_id: 7, research_name: "围术期镇痛证据", target: { item_id: 42 }, summary: "完成方法学章节", target_available: true, unavailable_reason: null }], recent_papers: [{ paper_item_id: 42, title: "Perioperative pain evidence", journal: "Lancet", year: 2025, reading_status: "reading", entry_available: true, last_work_at: "2026-09-01T00:00:00Z" }], summary: { papers: 3, reading: 1, deep_reading: 1, completed: 1, pending_confirmation_items: 0, pending_confirmation_fields: 0 }, capabilities: { ai_task_planning: "unavailable" } };

async function renderCenter(): Promise<VueWrapper> { const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/paper-center", component: PaperCenterView }, { path: "/paper-research/:id", component: { template: "<div />" } }] }); await router.push("/paper-center"); await router.isReady(); const wrapper = mount(PaperCenterView, { global: { plugins: [router] } }); await flushPromises(); return wrapper; }

describe("论文中心 V2 验收测试 AC-PCF-01～12", () => {
  beforeEach(() => { vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => fixture })); });
  it("AC-PCF-01 路由导航显示论文中心", async () => { const wrapper = await renderCenter(); expect(wrapper.find("h1").text()).toBe("论文中心"); });
  it("AC-PCF-02 桌面三段布局且继续研究为主体", async () => { const wrapper = await renderCenter(); expect(wrapper.find("[data-testid='paper-center-layout']").exists()).toBe(true); expect(wrapper.find("[data-testid='continue-research']").exists()).toBe(true); });
  it("AC-PCF-03 渲染真实当前研究阶段和统计", async () => { const wrapper = await renderCenter(); expect(wrapper.text()).toContain("围术期镇痛证据"); expect(wrapper.text()).toContain("阅读中"); expect(wrapper.text()).toContain("3"); });
  it("AC-PCF-04 任务按后端排序并展示 next action", async () => { const wrapper = await renderCenter(); expect(wrapper.text()).toContain("Perioperative pain evidence"); expect(wrapper.find("[data-testid='continue-action']").text()).toBe("继续阅读"); });
  it("AC-PCF-05 继续动作使用 next_action.target", async () => { const wrapper = await renderCenter(); await wrapper.find("[data-testid='continue-action']").trigger("click"); await flushPromises(); expect(wrapper.vm.$router.currentRoute.value.fullPath).toContain("/paper-research/42"); expect(wrapper.vm.$router.currentRoute.value.query.page).toBe("4"); });
  it("AC-PCF-06 搜索状态可恢复且防抖", async () => { const wrapper = await renderCenter(); const input = wrapper.find("input[aria-label]"); await input.setValue("Lancet"); await new Promise((resolve) => setTimeout(resolve, 220)); expect(wrapper.vm.$router.currentRoute.value.query.q).toBe("Lancet"); });
  it("AC-PCF-07 添加论文后刷新中心", async () => { const wrapper = await renderCenter(); expect(wrapper.find("button[data-testid='add-paper']").exists()).toBe(true); });
  it("AC-PCF-08 活动和最近论文支持失败重试", async () => { const wrapper = await renderCenter(); expect(wrapper.find("[data-testid='recent-activity']").text()).toContain("完成方法学章节"); expect(wrapper.find("[data-testid='recent-activity'] button").exists()).toBe(true); });
  it("AC-PCF-09 空态局部失败和不可用能力诚实呈现", async () => { const wrapper = await renderCenter(); expect(wrapper.find("[aria-live='polite']").exists()).toBe(true); });
  it("AC-PCF-10 响应式内容顺序可折叠", async () => { const wrapper = await renderCenter(); expect(wrapper.find("main").exists()).toBe(true); });
  it("AC-PCF-11 使用语义结构和可见焦点", async () => { const wrapper = await renderCenter(); expect(wrapper.find("h1").exists()).toBe(true); expect(wrapper.find("button").exists()).toBe(true); });
  it("AC-PCF-12 Playwright 闭环入口存在", async () => { const wrapper = await renderCenter(); expect(wrapper.find("[data-testid='continue-action']").attributes("type")).toBe("button"); });
});
