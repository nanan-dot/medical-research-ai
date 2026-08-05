import { mount } from "@vue/test-utils";
import { expect, test } from "vitest";

import type { RankedCitationItem } from "../../api/literatureSearch";
import PaperResults from "./PaperResults.vue";

const item = (pmid: string, overrides: Partial<RankedCitationItem["item"]> = {}): RankedCitationItem => ({
  item: {
    pmid,
    doi: null,
    title: `标题 ${pmid}`,
    authors: ["Kim J", "Lee S", "Wang L"],
    journal: "Nature Medicine",
    year: 2024,
    entry_type: "article",
    verified: true,
    verified_by: "pubmed",
    verified_on: "2026-08-05T00:00:00+00:00",
    has_abstract: true,
    publication_types: ["Journal Article"],
    ...overrides,
  },
  sort_reason: "relevance: ordered by PubMed default ranking for this search",
  state: { saved: false, read_status: "unread", tags: [], custom_order_index: null },
});

const items = [item("1"), item("2"), item("3")];

test("renders result cards with abstract, verified, and sort reason", () => {
  const wrapper = mount(PaperResults, {
    props: {
      items,
      loading: false,
      updating: {},
      currentPage: 1,
      totalPages: 2,
      filteredTotal: 21,
      hasPrevious: false,
      hasNext: true,
    },
  });

  expect(wrapper.text()).toContain("标题 1");
  expect(wrapper.text()).toContain("有摘要");
  expect(wrapper.text()).toContain("PubMed 已核实");
  expect(wrapper.text()).toContain("排序理由：relevance");
  expect(wrapper.text()).toContain("筛选后共 21 条");
});

test("emits toggle events and pagination navigation", async () => {
  const wrapper = mount(PaperResults, {
    props: {
      items,
      loading: false,
      updating: {},
      currentPage: 1,
      totalPages: 2,
      filteredTotal: 21,
      hasPrevious: false,
      hasNext: true,
    },
  });

  await wrapper.findAll(".state-chip")[0].trigger("click");
  expect(wrapper.emitted("toggleSaved")?.[0]).toEqual(["1", true]);

  await wrapper.findAll(".state-chip")[1].trigger("click");
  expect(wrapper.emitted("toggleRead")?.[0]).toEqual(["1", true]);

  // nav 结构：上一页 | 页码1 | 页码2 | 下一页；第 4 个按钮才是"下一页"。
  await wrapper.get("nav button:nth-child(4)").trigger("click");
  expect(wrapper.emitted("nextPage")).toHaveLength(1);

  await wrapper.get(".pagination .page-number.current").trigger("click");
  expect(wrapper.emitted("goToPage")).toBeUndefined();
});

test("shows empty state when no items", () => {
  const wrapper = mount(PaperResults, {
    props: {
      items: [],
      loading: false,
      updating: {},
      currentPage: 1,
      totalPages: 1,
      filteredTotal: 0,
      hasPrevious: false,
      hasNext: false,
    },
  });
  expect(wrapper.text()).toContain("当前筛选条件下没有结果");
});
