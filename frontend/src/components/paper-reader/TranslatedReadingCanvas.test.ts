import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import TranslatedReadingCanvas from "./TranslatedReadingCanvas.vue";

const bootstrap = {
  paper: { document_id: 7 },
  document: { file_hash: "a".repeat(64) },
  revision_fence: { anchor_revision_id: 2, segmentation_revision_id: 3 },
};

afterEach(() => vi.unstubAllGlobals());

describe("TranslatedReadingCanvas", () => {
  it("renders distinct bilingual and translated-only reading modes from cached revisions", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("source-segments")) {
        return Promise.resolve(new Response(JSON.stringify({
          anchor_revision_id: 2,
          segmentation_revision_id: 3,
          items: [{ id: 11, reading_order: 0, segment_type: "paragraph", text: "Dose 5 mg daily.", translation_eligibility: "eligible", fragments: [] }],
          total: 1,
        })));
      }
      if (url.includes("translation-segment-intents")) {
        return Promise.resolve(new Response(JSON.stringify({
          generation: "7:2:3",
          queued_count: 0,
          deduplicated_count: 1,
          items: [{
            segment_id: 11,
            translation_eligibility: "eligible",
            state: "cached",
            job: null,
            revision: { id: 31, document_id: 7, source_anchor_id: 41, version: 1, origin: "machine", source_language: "en", target_language: "zh-CN", translated_text: "每日服用 5 mg。", alignment: [], terms: [], issues: [], quality_status: "machine_checked", provider: "local", model: "medical", created_at: "2026-09-14T00:00:00Z" },
            degraded_reason: null,
          }],
        }), { status: 202 }));
      }
      throw new Error(`unexpected ${url}`);
    }));
    const wrapper = mount(TranslatedReadingCanvas, { props: { bootstrap, currentPage: 1, mode: "bilingual" } });
    await flushPromises();
    expect(wrapper.text()).toContain("Dose 5 mg daily.");
    expect(wrapper.text()).toContain("每日服用 5 mg。");

    await wrapper.setProps({ mode: "translated" });
    expect(wrapper.text()).not.toContain("Dose 5 mg daily.");
    expect(wrapper.text()).toContain("每日服用 5 mg。");
  });

  it("queues a visible page without falsely promoting its first segment to active selection", async () => {
    const requests: Array<Record<string, unknown>> = [];
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("source-segments")) return Promise.resolve(new Response(JSON.stringify({
        anchor_revision_id: 2, segmentation_revision_id: 3,
        items: [{ id: 11, reading_order: 0, segment_type: "paragraph", text: "Source", translation_eligibility: "eligible", fragments: [] }], total: 1,
      })));
      if (url.includes("translation-segment-intents")) {
        requests.push(JSON.parse(String(init?.body)));
        return Promise.resolve(new Response(JSON.stringify({ generation: "7:2:3", queued_count: 1, deduplicated_count: 0, items: [{ segment_id: 11, translation_eligibility: "eligible", state: "queued", job: null, revision: null, degraded_reason: null }] }), { status: 202 }));
      }
      throw new Error(`unexpected ${url}`);
    }));

    mount(TranslatedReadingCanvas, { props: { bootstrap, currentPage: 1, mode: "bilingual" } });
    await flushPromises();

    expect(requests[0]).toMatchObject({ trigger: "visible", active_segment_id: null });
  });
});
