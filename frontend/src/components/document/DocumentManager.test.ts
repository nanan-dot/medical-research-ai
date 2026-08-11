import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

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
};

const knowledgeSource = {
  id: 1,
  name: "肝癌免疫治疗资料",
  source_type: "local_folder",
  root_path: "H:\\research\\HCC-immunotherapy",
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
  it("shows truthful failure state and retries parsing", async () => {
    const fetchMock = buildFetchMock(
      { items: [failedDocument], total: 1, offset: 0, limit: 20 }, // documents 列表
      [],                                                          // knowledge-sources 列表
      { ...failedDocument, parse_status: "pending", error_code: null, error_message: null, retry_count: 2 }, // retry-parse 响应
    );
    const wrapper = mountManager();
    await flushPromises();

    // 状态 pill：解析失败 + 索引过期（outdated → "索引过期"）
    expect(wrapper.text()).toContain("失败");
    expect(wrapper.text()).toContain("索引过期");
    // 真实错误文案来自 error_message 字段
    expect(wrapper.text()).toContain("解析失败，可安全重试");
    // 左栏来源树渲染真实知识源（本次 mock 空数组 → 显示去添加引导）
    expect(wrapper.text()).toContain("去知识库添加资料文件夹");

    // 点击重试解析
    const retryButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("重试解析"));
    expect(retryButton).toBeTruthy();
    await retryButton!.trigger("click");
    await flushPromises();

    // 真实调用 retry-parse 接口
    expect(fetchMock.mock.calls).toContainEqual([
      "/api/v1/documents/7/retry-parse",
      expect.objectContaining({ method: "POST" }),
    ]);
    // 重试后错误文案消失
    expect(wrapper.text()).not.toContain("解析失败，可安全重试");
  });

  it("applies status filters through the API", async () => {
    const fetchMock = buildFetchMock(
      { items: [], total: 0, offset: 0, limit: 20 }, // documents 列表
      [],                                            // knowledge-sources 列表
      { items: [], total: 0, offset: 0, limit: 20 }, // 筛选后 documents
    );
    const wrapper = mountManager();
    await flushPromises();

    expect((wrapper.get(".indexed-only input").element as HTMLInputElement).checked).toBe(false);
    expect(String(fetchMock.mock.calls[0][0])).not.toContain("research_ready=true");

    const selects = wrapper.get(".filters").findAll("select");
    await selects[0].setValue("failed");
    await wrapper.get(".filters").trigger("submit");
    await flushPromises();

    expect(
      fetchMock.mock.calls.some(([url]) => String(url).includes("parse_status=failed")),
    ).toBe(true);
  });

  it("uploads a PDF and reloads the document list", async () => {
    const uploadedDocument = {
      ...failedDocument,
      id: 12,
      file_path: "documents/managed.pdf",
      original_filename: "uploaded.pdf",
      media_type: "application/pdf",
      parse_status: "pending",
      index_status: "pending",
      error_code: null,
      error_message: null,
    };
    const fetchMock = buildFetchMock(
      { items: [], total: 0, offset: 0, limit: 20 },                          // 挂载：documents
      [],                                                                     // 挂载：knowledge-sources
      {
        document: uploadedDocument,
        asset: {
          id: 1,
          asset_kind: "upload",
          original_filename: "uploaded.pdf",
          stored_relative_path: "documents/managed.pdf",
          media_type: "application/pdf",
          byte_size: 512,
          sha256: "a".repeat(64),
          processing_status: "pending_parse",
          created_at: "2026-08-10T00:00:00Z",
        },
        auto_parse_started: false,
        parse_trigger_url: "/api/v1/documents/12/parse",
      }, // 上传接口 201
      { items: [uploadedDocument], total: 1, offset: 0, limit: 20 },          // 上传后刷新 documents
    );
    const wrapper = mountManager();
    await flushPromises();

    const input = wrapper.get(".upload-panel input[type=file]").element as HTMLInputElement;
    const pdf = new File(["%PDF-1.7"], "uploaded.pdf", { type: "application/pdf" });
    Object.defineProperty(input, "files", { configurable: true, value: [pdf] });
    await wrapper.get(".upload-panel input[type=file]").trigger("change");
    await flushPromises();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/document-uploads",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/api/v1/documents?"))).toBe(true);
    expect(wrapper.text()).toContain("uploaded.pdf");
  });
});
