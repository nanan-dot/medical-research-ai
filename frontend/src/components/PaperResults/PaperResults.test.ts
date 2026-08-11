import { mount } from "@vue/test-utils";
import { expect, test } from "vitest";

import type { RankedCitationItem } from "../../api/literatureSearch";
import PaperResults from "./PaperResults.vue";

const routerStubs = { RouterLink: { template: "<a><slot /></a>" } };

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
    abstract: "This is the real abstract returned by the server.",
    publication_types: ["Journal Article"],
    ...overrides,
  },
  sort_reason: "relevance: ordered by PubMed default ranking for this search",
  state: { saved: false, read_status: "unread", tags: [], custom_order_index: null },
  library_item: null,
});

const items = [item("1"), item("2"), item("3")];

test("renders compact result records with server metadata, verified state, and sort reason", () => {
  const wrapper = mount(PaperResults, {
    global: { stubs: routerStubs },
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
  expect(wrapper.text()).toContain("展开摘要");
  expect(wrapper.text()).toContain("PubMed 已核实");
  expect(wrapper.text()).toContain("排序理由：relevance");
  expect(wrapper.text()).toContain("筛选后共 21 条");
});

test("renders a safe PubMed link and discloses only the returned abstract text", async () => {
  const wrapper = mount(PaperResults, {
    global: { stubs: routerStubs },
    props: { items: [item("12345")], loading: false, updating: {}, currentPage: 1, totalPages: 1, filteredTotal: 1, hasPrevious: false, hasNext: false },
  });

  const link = wrapper.get('a[href="https://pubmed.ncbi.nlm.nih.gov/12345/"]');
  expect(link.attributes("target")).toBe("_blank");
  expect(link.attributes("rel")).toBe("noopener noreferrer");
  expect(wrapper.text()).not.toContain("This is the real abstract returned by the server.");

  await wrapper.get(".abstract-disclosure button").trigger("click");
  expect(wrapper.text()).toContain("This is the real abstract returned by the server.");
});

test("states that an omitted abstract is unavailable without an expansion control", () => {
  const wrapper = mount(PaperResults, {
    global: { stubs: routerStubs },
    props: { items: [item("12345", { has_abstract: false, abstract: null })], loading: false, updating: {}, currentPage: 1, totalPages: 1, filteredTotal: 1, hasPrevious: false, hasNext: false },
  });

  expect(wrapper.text()).toContain("摘要不可用");
  expect(wrapper.find(".abstract-disclosure button").exists()).toBe(false);
});

test("emits toggle events and pagination navigation", async () => {
  const wrapper = mount(PaperResults, {
    global: { stubs: routerStubs },
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

  await wrapper.findAll(".action-button")[0].trigger("click");
  expect(wrapper.emitted("toggleSaved")?.[0]).toEqual(["1", true]);

  await wrapper.findAll(".action-button")[1].trigger("click");
  expect(wrapper.emitted("toggleRead")?.[0]).toEqual(["1", true]);

  // nav 结构：上一页 | 页码1 | 页码2 | 下一页；第 4 个按钮才是"下一页"。
  await wrapper.get("nav button:nth-child(4)").trigger("click");
  expect(wrapper.emitted("nextPage")).toHaveLength(1);

  await wrapper.get(".pagination button.current").trigger("click");
  expect(wrapper.emitted("goToPage")).toBeUndefined();
});

test("shows empty state when no items", () => {
  const wrapper = mount(PaperResults, {
    global: { stubs: routerStubs },
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
