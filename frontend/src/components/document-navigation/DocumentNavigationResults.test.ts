import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import DocumentNavigationResults from "./DocumentNavigationResults.vue";

describe("DocumentNavigationResults", () => {
  it("shows retrieval strategy and never presents an unverified condition as satisfied", () => {
    const wrapper = mount(DocumentNavigationResults, {
      props: { loading: false, error: null, result: { query: "近三年 RCT", knowledge_source_id: null, indexed_only: true, searchable_document_count: 1, strategy: "bm25", fallback_reason: "本机语义向量未启用", conditions: [{ label: "近三年", status: "unverified", reason: "没有年份依据" }], results: [{ document_id: 1, title: "本地文档", filename: "local.pdf", knowledge_source_id: 1, knowledge_source_name: "资料夹", relative_path: "trials/local.pdf", match_reason: "bm25 召回的本地原文块", location: { page_number: 2, section: null }, excerpt: "原文摘录", retrieval_score: 0.5, condition_status: [{ label: "随机对照试验", status: "unverified", reason: "没有试验类型依据" }] }] } },
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
    });
    expect(wrapper.text()).toContain("BM25 检索");
    expect(wrapper.text()).toContain("未验证，仅检索相关");
    expect(wrapper.text()).not.toContain("原文已验证");
    expect(wrapper.text()).toContain("第 2 页");
  });
});
