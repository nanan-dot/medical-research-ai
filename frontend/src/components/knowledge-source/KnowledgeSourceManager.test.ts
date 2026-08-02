import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import KnowledgeSourceManager from "./KnowledgeSourceManager.vue";

const source = {
  id: 1,
  name: "实验论文",
  source_type: "local_folder",
  root_path: "H:\\papers",
  enabled: true,
  sync_status: "idle",
  last_sync_time: null,
  error_message: null,
};

afterEach(() => vi.unstubAllGlobals());

describe("KnowledgeSourceManager", () => {
  it("renders backend state and can disable a source", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([source]), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...source, enabled: false }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchMock);

    const wrapper = mount(KnowledgeSourceManager);
    await flushPromises();
    expect(wrapper.text()).toContain("实验论文");
    expect(wrapper.text()).toContain("1 个来源 · 1 个启用");

    await wrapper.get(".source-actions button").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("1 个来源 · 0 个启用");
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/v1/knowledge-sources/1",
      expect.objectContaining({ method: "PATCH" }),
    );
  });

  it("shows explicit unavailable state and safe error text", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify([
            { ...source, sync_status: "unavailable", error_message: "目录已移动" },
          ]),
          { status: 200 },
        ),
      ),
    );
    const wrapper = mount(KnowledgeSourceManager);
    await flushPromises();
    expect(wrapper.text()).toContain("不可用");
    expect(wrapper.get('[role="alert"]').text()).toBe("目录已移动");
  });
});
