import { defineComponent, h } from "vue";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import DocumentsView from "./DocumentsView.vue";

describe("DocumentsView", () => {
  it("uses the 资料库 product copy and delegates both heading actions", async () => {
    const openImport = vi.fn();
    const manageSources = vi.fn();
    const DocumentManagerStub = defineComponent({
      name: "DocumentManager",
      setup(_, { expose }) {
        expose({ openImport, manageSources });
        return () => h("div", { "data-testid": "document-manager" });
      },
    });
    const wrapper = mount(DocumentsView, {
      global: { stubs: { DocumentManager: DocumentManagerStub } },
    });

    expect(wrapper.get("h1").text()).toBe("资料库");
    expect(wrapper.text()).toContain("管理进入研究体系的资料，并提供检索、问答与分析能力");
    await wrapper.get("button.manage-button").trigger("click");
    await wrapper.get("button.import-button").trigger("click");

    expect(manageSources).toHaveBeenCalledOnce();
    expect(openImport).toHaveBeenCalledOnce();
  });
});
