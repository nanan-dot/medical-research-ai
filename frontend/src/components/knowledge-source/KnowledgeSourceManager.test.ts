import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import KnowledgeSourceManager from "./KnowledgeSourceManager.vue";

const source = { id: 1, name: "实验论文", source_type: "local_folder", root_path: "H:\\papers", enabled: true, auto_sync: true, is_pinned: false, sync_status: "completed", health_status: "ready", last_sync_time: null, error_message: null, stats: { total_files: 3, parsed: 3, indexed: 2, pending: 1, failed: 0, available: 2, processing: 1, needs_attention: 0, availability_percent: 66.7 } };
const summary = { source_count: 1, local_folder_count: 1, obsidian_count: 0, total_item_count: 3, available_item_count: 2, processing_item_count: 1, needs_attention_count: 0, affected_source_count: 0, availability_percent: 66.7, issue_breakdown: { parse_failed: 0, unsupported_format: 0, unavailable_file: 0, index_failed: 0, other: 0 } };
function response(url: string) { return new Response(JSON.stringify(url.includes("summary") ? summary : { items: [source], total: 1, offset: 0, limit: 10 }), { status: 200 }); }
async function mountManager() { const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/sources", component: KnowledgeSourceManager }, { path: "/documents", component: { template: "<div />" } }] }); await router.push("/sources"); await router.isReady(); return { router, wrapper: mount(KnowledgeSourceManager, { global: { plugins: [router] } }) }; }
afterEach(() => vi.unstubAllGlobals());
describe("KnowledgeSourceManager", () => {
  it("maps real page and summary responses into the source row", async () => { vi.stubGlobal("fetch", vi.fn((url: string) => Promise.resolve(response(url)))); const { wrapper } = await mountManager(); await flushPromises(); expect(wrapper.text()).toContain("实验论文"); expect(wrapper.text()).toContain("知识来源"); });
  it("navigates to documents with the real knowledge_source_id query", async () => { vi.stubGlobal("fetch", vi.fn((url: string) => Promise.resolve(response(url)))); const { router, wrapper } = await mountManager(); await flushPromises(); await wrapper.get(".actions button:nth-child(2)").trigger("click"); await flushPromises(); expect(router.currentRoute.value.query.knowledge_source_id).toBe("1"); });
});
