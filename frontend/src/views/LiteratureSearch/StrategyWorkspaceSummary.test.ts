import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import StrategyWorkspaceSummary from "./StrategyWorkspaceSummary.vue";

const strategy = {
  id: 1,
  research_question: "ILD patients receiving antifibrotic therapy",
  intent_mode: "pico",
  intent: {},
  limits: { database: "pubmed" },
  query_text: "ILD[tiab]",
  query_source: "generated" as const,
  fingerprint: "fingerprint",
  revision: 2,
  generation_state: "ready",
  validation_state: "stale",
  count_state: "stale",
  count: {},
  last_saved_at: "2026-08-23T00:00:00Z",
  terms: [{ id: 2, concept_group: "disease", text: "interstitial lung disease", source: "research_question" as const, field_tag: "tiab", relation_type: null, is_locked: true, warning: null }],
  mesh_terms: [{ id: 3, descriptor: "Lung Diseases, Interstitial", mesh_id: "D008410", concept_group: "disease", source: "nlm_mesh" as const, verification_status: "verified" as const, is_locked: false, verification_checked_at: "2026-08-23T00:00:00Z" }],
};

describe("StrategyWorkspaceSummary", () => {
  it("renders backend-owned strategy state and emits real refresh actions", async () => {
    const wrapper = mount(StrategyWorkspaceSummary, {
      props: { strategy, validation: null, count: null, actionLoading: false, actionError: null },
    });

    expect(wrapper.text()).toContain("1 个检索术语 · 1 个已验证 MeSH");
    expect(wrapper.text()).toContain("匹配数量需要刷新");
    await wrapper.get("button").trigger("click");
    expect(wrapper.emitted("refreshMesh")).toHaveLength(1);
  });
});
