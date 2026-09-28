import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import DocumentManager from "./DocumentManager.vue";

const item = {
  id: 7, knowledge_source_id: 1, file_path: "ild/paper.pdf", original_filename: "paper.pdf", media_type: "application/pdf", file_hash: "hash", file_size: 512, modified_time: "2026-08-10T00:00:00Z", scan_state: "pending", parse_status: "succeeded", index_status: "succeeded", error_code: null, error_message: null, retry_count: 0, started_at: null, finished_at: null, parsed_is_scanned: false,
  source_name: "ILD 核心文献", source_type: "local_folder", relative_path: "ild/paper.pdf", display_name: "paper.pdf", task_status: null, phase: null, current_item: null, last_opened_at: null, open_count: 0, status: "ai_available", match_fields: [], snippet: null, locator: null,
};

function installApiFixture() {
  const fetchMock = vi.fn((url: string) => {
    if (url.includes("/summary")) return new Response(JSON.stringify({ total: 1, processed: 1, ai_available: 1, processing: 0, needs_attention: 0, issue_breakdown: {}, source_types: [], snapshot_at: "2026-08-30T00:00:00Z" }));
    if (url.includes("/source-tree")) return new Response(JSON.stringify({ groups: [{ source_type: "local", node_id: "group:local", descendant_count: 1, health: "ready", children: [{ node_id: "source:1", parent_id: "group:local", name: "ILD 核心文献", relative_path: "", source_id: 1, direct_count: 1, descendant_count: 1, health: "ready", children: [] }] }] }));
    if (url.includes("/recent")) return new Response(JSON.stringify({ items: [], total: 0, offset: 0, limit: 5 }));
    if (url.includes("/storage")) return new Response(JSON.stringify({ managed_bytes: 512, external_source_bytes: 0, total_known_bytes: 512, quota_bytes: null, usage_percent: null, status: "not_configured", measured_at: "2026-08-30T00:00:00Z" }));
    if (url.includes("/facets")) return new Response(JSON.stringify({ sources: [], source_types: [], file_types: [], statuses: [] }));
    if (url.includes("/opened")) return new Response(JSON.stringify({ document_id: 7, open_count: 1, last_opened_at: null, last_opened_by: null }));
    if (url.includes("/items")) return new Response(JSON.stringify({ items: [item], total: 1, offset: 0, limit: 25 }));
    return new Response(JSON.stringify({ detail: "not found" }), { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("DocumentManager", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("uses the unified library API and preserves every selected source in the URL", async () => {
    const fetchMock = installApiFixture();
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/documents", component: { template: "<div />" } }, { path: "/documents/:id", component: { template: "<div />" } }, { path: "/sources", component: { template: "<div />" } }] });
    await router.push("/documents?sourceIds=1,2&page=1&pageSize=25&sort=updated_at&order=desc");
    await router.isReady();
    const wrapper = mount(DocumentManager, { global: { plugins: [router] } });
    await flushPromises();

    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/api/v1/library/items?") && String(url).includes("source_id=1") && String(url).includes("source_id=2"))).toBe(true);
    expect(wrapper.text()).toContain("当前视图：ILD 核心文献");
    await wrapper.get(".all-resources").trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query.sourceIds).toBeUndefined();
    expect(router.currentRoute.value.query.page).toBe("1");
  });

  it("opens a resource through the real opened endpoint without changing the source filter", async () => {
    const fetchMock = installApiFixture();
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/documents", component: { template: "<div />" } }, { path: "/documents/:id", component: { template: "<div />" } }, { path: "/sources", component: { template: "<div />" } }] });
    await router.push("/documents?sourceId=1&page=1&pageSize=25&sort=updated_at&order=desc");
    await router.isReady();
    const wrapper = mount(DocumentManager, { global: { plugins: [router] } });
    await flushPromises();

    void wrapper.get('[aria-label="查看 paper.pdf"]').trigger("click");
    await Promise.resolve();
    await flushPromises();
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/api/v1/library/items/7/opened"))).toBe(true);
    expect(router.currentRoute.value.query.sourceIds).toBe("1");
    expect(router.currentRoute.value.query.documentId).toBe("7");
  });

  it("offers the source rail as a closable drawer control for compact layouts", async () => {
    installApiFixture();
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/documents", component: { template: "<div />" } }, { path: "/documents/:id", component: { template: "<div />" } }, { path: "/sources", component: { template: "<div />" } }] });
    await router.push("/documents?page=1&pageSize=25&sort=updated_at&order=desc");
    await router.isReady();
    const wrapper = mount(DocumentManager, { global: { plugins: [router] } });
    await flushPromises();

    await wrapper.get(".rail-toggle").trigger("click");
    expect(wrapper.get(".source-nav").classes()).toContain("is-open");
    await wrapper.get(".rail-close").trigger("click");
    expect(wrapper.get(".source-nav").classes()).not.toContain("is-open");
  });
});
