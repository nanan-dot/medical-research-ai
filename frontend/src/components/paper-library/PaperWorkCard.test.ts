import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { PaperItem } from "../../api/paperLibrary";
import PaperWorkCard from "./PaperWorkCard.vue";

const paper: PaperItem = {
  id: 7,
  pmid: "32970396",
  doi: "10.1056/NEJMoa2024816",
  title: "Dapagliflozin in Patients with Chronic Kidney Disease",
  authors: "Heerspink HJL; Stefánsson BV",
  journal: "NEJM",
  year: 2020,
  paper_type: "RCT",
  journal_quartile: "Q1",
  journal_quartile_source: "Scimago",
  journal_quartile_year: 2020,
  metadata_status: "succeeded",
  metadata_source: "pubmed",
  metadata_retryable: false,
  metadata_error_code: null,
  document_id: 12,
  fulltext_status: "ready",
  reading_status: "reading",
  reading_progress_percent: 68,
  current_section: "Results",
  analysis_status: "analyzing",
  analysis_progress: { completed: 8, total: 12 },
  primary_relation: { research_context_id: 3, research_name: "SGLT2 治疗 CKD 研究", role: "core_evidence", note: null, version: 1 },
  additional_relation_count: 2,
  recent_activity: { id: 1, kind: "analysis_updated", detail: "完成「研究结果」分析", created_at: "2026-09-01T10:30:00Z" },
  tags: ["肾脏"],
  can_read: true,
  can_analyze: true,
  capability_reason: null,
  preferred_work_action: "analysis",
  last_work_at: "2026-09-01T10:30:00Z",
  reading_entry: { action: "continue", enabled: true, reason: null },
  analysis_entry: { action: "continue", enabled: true, reason: null },
};

describe("PaperWorkCard", () => {
  it("shows reading progress and exposes only the reading action", () => {
    const wrapper = mount(PaperWorkCard, { props: { paper, selected: true } });

    expect(wrapper.text()).toContain("Results · 68%");
    expect(wrapper.text()).toContain("SGLT2 治疗 CKD 研究");
    expect(wrapper.text()).toContain("+2");
    expect(wrapper.get("button.primary-action").text()).toBe("继续阅读");
    expect(wrapper.find("button.secondary-action").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("8 / 12");
    expect(wrapper.text()).not.toContain("继续分析");
  });

  it("disables an unavailable entry and exposes its server reason", () => {
    const wrapper = mount(PaperWorkCard, {
      props: {
        paper: {
          ...paper,
          preferred_work_action: "reading",
          reading_entry: { action: "continue", enabled: false, reason: "全文尚未处理完成" },
        },
        selected: false,
      },
    });

    const primary = wrapper.get("button.primary-action");
    expect(primary.attributes("disabled")).toBeDefined();
    expect(primary.attributes("title")).toBe("全文尚未处理完成");
  });
});
