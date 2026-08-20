import { flushPromises, mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import DocumentManager from "./DocumentManager.vue";

const failedDocument = {
  id: 7,
  knowledge_source_id: 1,
  file_path: "paper.md",
  file_hash: "a".repeat(64),
  file_size: 42,
  modified_time: "2026-08-02T00:00:00Z",
  scan_state: "outdated",
  parse_status: "failed",
  index_status: "outdated",
  error_code: "parse_failed",
  error_message: "解析失败，可安全重试",
  retry_count: 1,
  started_at: null,
  finished_at: "2026-08-02T00:01:00Z",
  health_status: "needs_attention",
  health_reason: "解析失败，可安全重试",
  available_actions: ["repair"],
};

const knowledgeSource = {
  id: 1,
  name: "肝癌免疫治疗资料",
  source_type: "local_folder",
  root_path: "H:\\\\research\\\\HCC-immunotherapy",
  enabled: true,
  sync_status: "completed",
  last_sync_time: "2026-08-11T06:32:00Z",
  error_message: null,
  stats: { total_files: 126, parsed: 112, indexed: 112, pending: 8, failed: 6 },
};
// eslint-disable-next-line @typescript-eslint/no-unused-vars -- 夹具保留作文档参考（mock 响应形状）
void knowledgeSource;

afterEach(() => vi.unstubAllGlobals());

/** 构造按调用顺序消费的 fetch mock。
 *  挂载时调用顺序：watch(sourceId, immediate) → documents 列表接口；
 *  onMounted → loadSources() → knowledge-sources 列表接口。
 *  因此第一个响应给 documents，第二个给 knowledge-sources。 */
function buildFetchMock(...responses: unknown[]): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn();
  responses.forEach((payload) => {
    fetchMock.mockResolvedValueOnce(
      payload instanceof Response ? payload : new Response(JSON.stringify(payload)),
    );
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function mountManager(): ReturnType<typeof mount> {
  return mount(DocumentManager, {
    global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
  });
}

describe("DocumentManager", () => {
  it("does not restore a direct document upload entry", () => {
    const source = readFileSync("src/components/document/DocumentManager.vue", "utf8");

    expect(source).not.toContain("DocumentUploadPanel");
    expect(source).not.toContain("useDocumentUpload");
    expect(source).not.toContain("uploadPdf");
  });

  it("does not expose a content/full-text mode in the document library", () => {
    const source = readFileSync("src/components/document/DocumentManager.vue", "utf8");

    expect(source).not.toContain("正文定位");
    expect(source).not.toContain("mode-switch");
    expect(source).not.toContain("searchContent");
  });

  it("shows truthful failure state and retries parsing", async () => {
    const fetchMock = buildFetchMock(
      { items: [failedDocument], total: 1, offset: 0, limit: 20 }, // documents 列表
      [],                                                          // knowledge-sources 列表
      { total_item_count: 1, available_item_count: 0, processing_item_count: 0, needs_attention_count: 1 }, // 全库统计
      { document_id: 7, action: "repair", task_id: 12, status: "queued", health_status: "needs_attention" }, // 统一 repair 响应
      { items: [{ ...failedDocument, parse_status: "pending", error_code: null, error_message: null, retry_count: 2, health_status: "processing", health_reason: "等待解析" }], total: 1, offset: 0, limit: 20 }, // repair 后重载
    );
    const wrapper = mountManager();
    await flushPromises();

    expect(wrapper.text()).toContain("需处理");
    expect(wrapper.text()).toContain("解析失败，可安全重试");
    // 来源树常驻桌面侧栏；不再有“全部文档 / 按来源浏览”分段切换。
    expect(wrapper.text()).toContain("知识来源");
    expect(wrapper.text()).not.toContain("按来源浏览");
    expect(wrapper.text()).not.toContain("资料范围");

    const retryButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("修复"));
    expect(retryButton).toBeTruthy();
    await retryButton!.trigger("click");
    await flushPromises();

    expect(fetchMock.mock.calls).toContainEqual([
      "/api/v1/documents/7/repair",
      expect.objectContaining({ method: "POST" }),
    ]);
    expect(wrapper.text()).not.toContain("解析失败，可安全重试");
  });

  it("applies health and file-type filters through the API", async () => {
    const fetchMock = buildFetchMock(
      { items: [], total: 0, offset: 0, limit: 20 }, // documents 列表
      [],                                            // knowledge-sources 列表
      { total: 0, available: 0, processing: 0, needs_attention: 0 }, // 文档统计
      { items: [], total: 0, offset: 0, limit: 25 }, // 筛选后 documents
    );
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/documents", component: { template: "<div />" } }] });
    await router.push("/documents");
    await router.isReady();
    const wrapper = mount(DocumentManager, { global: { plugins: [router] } });
    await flushPromises();

    const selects = wrapper.get(".document-filters").findAll("select");
    await selects[0].setValue("pdf");
    await selects[1].setValue("needs_attention");
    await wrapper.get(".document-filters").trigger("submit");
    await flushPromises();

    expect(
      fetchMock.mock.calls.some(([url]) => String(url).includes("file_type=pdf") && String(url).includes("health_status=needs_attention")),
    ).toBe(true);
  });

  it("keeps sourceId in the URL and applies it to the document request", async () => {
    const fetchMock = buildFetchMock(
      { items: [], total: 0, offset: 0, limit: 20 },
      [knowledgeSource],
      { items: [], total: 0, offset: 0, limit: 20 },
    );
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/documents", component: { template: "<div />" } }],
    });
    await router.push("/documents?sourceId=1");
    await router.isReady();

    const wrapper = mount(DocumentManager, { global: { plugins: [router] } });
    await flushPromises();

    expect(String(fetchMock.mock.calls[0][0])).toContain("knowledge_source_id=1");
    await wrapper.find(".scope-item").trigger("click");
    await flushPromises();

    expect(router.currentRoute.value.fullPath).toBe("/documents?view=all&sort=updated_at_desc&page=1&pageSize=25");
    expect(fetchMock.mock.calls.some(([url]) => !String(url).includes("knowledge_source_id=1"))).toBe(true);
  });
});
