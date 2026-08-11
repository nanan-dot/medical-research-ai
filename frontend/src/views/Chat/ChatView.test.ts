import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";
import ChatView from "./ChatView.vue";

afterEach(() => vi.restoreAllMocks());

test("opens citation evidence", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 1, document_ids: [2], title: null, research_context_id: null, messages: [] }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 4, role: "assistant", content: "120 participants", citations: [{ id: 9, document_id: 2, page: 6, section: null, evidence_text: "120 were enrolled", citation_text: "Trial", retrieval_score: .9 }] }) });
  vi.stubGlobal("fetch", fetchMock);
  const wrapper = mount(ChatView);
  await flushPromises();
  await wrapper.get("input").setValue("2");
  await wrapper.get("form").trigger("submit");
  await flushPromises();
  await wrapper.get("input").setValue("How many?");
  await wrapper.get("form").trigger("submit");
  await flushPromises();
  expect(wrapper.text()).toContain("120 participants");
  await wrapper.get(".citations button").trigger("click");
  expect(wrapper.text()).toContain("120 were enrolled");
  expect(wrapper.text()).toContain("6");
});
