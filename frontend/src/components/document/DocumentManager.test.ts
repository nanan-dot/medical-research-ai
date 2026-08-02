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

afterEach(() => vi.unstubAllGlobals());

describe("DocumentManager", () => {
  it("shows truthful failure state and retries parsing", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ items: [failedDocument], total: 1, offset: 0, limit: 20 })),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...failedDocument, parse_status: "pending", error_code: null, error_message: null, retry_count: 2 })),
      );
    vi.stubGlobal("fetch", fetchMock);
    const wrapper = mount(DocumentManager);
    await flushPromises();

    expect(wrapper.text()).toContain("解析失败，可安全重试");
    expect(wrapper.text()).toContain("已过期");
    await wrapper.get(".actions button").trigger("click");
    await flushPromises();
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/v1/documents/7/retry-parse",
      expect.objectContaining({ method: "POST" }),
    );
    expect(wrapper.text()).not.toContain("解析失败，可安全重试");
  });

  it("applies status filters through the API", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0, offset: 0, limit: 20 })),
    );
    vi.stubGlobal("fetch", fetchMock);
    const wrapper = mount(DocumentManager);
    await flushPromises();
    const selects = wrapper.findAll("select");
    await selects[0].setValue("failed");
    await wrapper.get(".filters").trigger("submit");
    await flushPromises();
    expect(String(fetchMock.mock.calls.at(-1)?.[0])).toContain("parse_status=failed");
  });
});
