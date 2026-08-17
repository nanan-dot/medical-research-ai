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
  expect(wrapper.find(".ranking-disclosure").exists()).toBe(false);
  expect(wrapper.text()).not.toContain("结果概览");
  expect(wrapper.text()).not.toContain("筛选后共 21 条");
  expect(wrapper.text()).toContain("共 21 条 · 当前显示第 1–21 条");
  expect(wrapper.get(".reading-signals").text()).toContain("Journal Article");
  expect(wrapper.find(".results-navigation").exists()).toBe(true);
});

test("shows the actual range for each paginated result page and hides it for no results", () => {
  const pageTwo = mount(PaperResults, {
    global: { stubs: routerStubs },
    props: { items, loading: false, updating: {}, currentPage: 2, pageSize: 100, totalPages: 5, filteredTotal: 500, hasPrevious: true, hasNext: true },
  });
  const empty = mount(PaperResults, {
    global: { stubs: routerStubs },
    props: { items: [], loading: false, updating: {}, currentPage: 1, pageSize: 100, totalPages: 1, filteredTotal: 0, hasPrevious: false, hasNext: false },
  });
  expect(pageTwo.text()).toContain("共 500 条 · 当前显示第 101–200 条");
  expect(pageTwo.get(".navigation-controls").text()).toContain("上一页");
  expect(pageTwo.get(".navigation-controls").text()).toContain("第 2 页，共 5 页");
  expect(pageTwo.get(".navigation-controls").text()).toContain("下一页");
  expect(empty.find(".range-note").exists()).toBe(false);
  expect(empty.find(".results-navigation").exists()).toBe(false);
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
  await wrapper.get(".pagination:not(.pagination-top) button:nth-child(4)").trigger("click");
  expect(wrapper.emitted("nextPage")).toHaveLength(1);

  await wrapper.get(".pagination button.current").trigger("click");
  expect(wrapper.emitted("goToPage")).toBeUndefined();
});

test("provides previous, current page, and next controls at the end of the result list", async () => {
  const wrapper = mount(PaperResults, {
    global: { stubs: routerStubs },
    props: { items, loading: false, updating: {}, currentPage: 2, totalPages: 5, filteredTotal: 500, hasPrevious: true, hasNext: true },
  });

  const pagination = wrapper.get(".pagination:not(.pagination-top)");
  await pagination.get("button:first-child").trigger("click");
  await pagination.get("button:last-child").trigger("click");
  expect(wrapper.emitted("previousPage")).toHaveLength(1);
  expect(wrapper.emitted("nextPage")).toHaveLength(1);
});

test("emits the shared pagination events from the top results navigation", async () => {
  const wrapper = mount(PaperResults, {
    global: { stubs: routerStubs },
    props: { items, loading: false, updating: {}, currentPage: 2, totalPages: 5, filteredTotal: 500, hasPrevious: true, hasNext: true },
  });

  const controls = wrapper.get(".navigation-controls");
  await controls.get('button[aria-label="上一页"]').trigger("click");
  await controls.get('button[aria-label="下一页"]').trigger("click");
  expect(wrapper.emitted("previousPage")).toHaveLength(1);
  expect(wrapper.emitted("nextPage")).toHaveLength(1);
});

test("keeps only the range note when there is one result page", () => {
  const wrapper = mount(PaperResults, {
    global: { stubs: routerStubs },
    props: { items, loading: false, updating: {}, currentPage: 1, totalPages: 1, filteredTotal: 3, hasPrevious: false, hasNext: false },
  });

  expect(wrapper.find(".results-navigation").exists()).toBe(true);
  expect(wrapper.find(".navigation-controls").exists()).toBe(false);
});

test("groups saved, library, and read controls in a vertical action rail", () => {
  const wrapper = mount(PaperResults, {
    global: { stubs: routerStubs },
    props: {
      resultId: 9,
      items: [item("12345")],
      loading: false,
      updating: {},
      currentPage: 1,
      totalPages: 1,
      filteredTotal: 1,
      hasPrevious: false,
      hasNext: false,
    },
  });

  const rail = wrapper.get(".record-actions--rail");
  expect(rail.text()).toContain("保存");
  expect(rail.text()).toContain("加入知识库");
  expect(rail.text()).toContain("标记已读");
  expect(rail.classes()).toContain("record-actions--rail");
  expect(rail.classes()).toContain("record-actions--horizontal");
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
