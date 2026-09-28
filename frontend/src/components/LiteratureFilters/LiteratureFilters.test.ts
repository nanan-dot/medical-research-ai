import { mount } from "@vue/test-utils";
import { expect, test } from "vitest";

import type { ResultFilterValues } from "../../api/literatureSearch";
import LiteratureFilters from "./LiteratureFilters.vue";

const filters: ResultFilterValues = {
  year: null, publication_type: "", journal: "", author: "", has_abstract: null,
  saved: null, read_status: "", tags: "", sort: "relevance",
};

test("keeps sorting rationale collapsed until the user requests it", async () => {
  const wrapper = mount(LiteratureFilters, { props: { filters, disabled: false } });
  const help = wrapper.get(".sort-help");

  expect(help.get("summary").text()).toBe("排序依据");
  expect(help.attributes("open")).toBeUndefined();

  await help.get("summary").trigger("click");
  expect(help.attributes("open")).toBeDefined();
  expect(help.text()).toContain("按 PubMed 本次返回顺序展示");
});

test("updates sorting rationale and still emits apply when sorting changes", async () => {
  const wrapper = mount(LiteratureFilters, { props: { filters, disabled: false } });
  await wrapper.get(".sort-control select").setValue("recommended");

  expect(wrapper.emitted("apply")?.[0][0]).toMatchObject({ sort: "recommended" });
  await wrapper.get(".sort-help summary").trigger("click");
  expect(wrapper.get(".sort-help").text()).toContain("阅读优先级");
});

test("uses native accessible controls for sort and rationale disclosure", () => {
  const wrapper = mount(LiteratureFilters, { props: { filters, disabled: false } });
  expect(wrapper.get(".sort-control select").element.tagName).toBe("SELECT");
  expect(wrapper.get(".sort-help summary").element.tagName).toBe("SUMMARY");
});

test("exposes server-provided facet values without constraining manual filter input", () => {
  const wrapper = mount(LiteratureFilters, {
    props: {
      filters,
      disabled: false,
      facets: { year: { "2024": 3 }, journal: { "Test Journal": 2 }, publication_type: { Review: 1 } },
    },
  });

  expect(wrapper.get("#result-year-facets").text()).toContain("2024（3）");
  expect(wrapper.get("#result-journal-facets").text()).toContain("Test Journal（2）");
  expect(wrapper.get("#result-publication-type-facets").text()).toContain("Review（1）");
});

test("disables a score sort only when the server says its signal is unavailable", () => {
  const wrapper = mount(LiteratureFilters, {
    props: { filters, disabled: false, sortCapabilities: { popular: { available: false, reason: "尚无开放数据" } } },
  });
  const option = wrapper.get('option[value="popular"]');
  expect(option.attributes("disabled")).toBeDefined();
  expect(option.text()).toContain("不可用");
});

test("renders an applied filter as a removable chip", async () => {
  const wrapper = mount(LiteratureFilters, { props: { filters: { ...filters, journal: "Test Journal" }, disabled: false } });
  await wrapper.get(".applied-filters button").trigger("click");
  expect(wrapper.emitted("apply")?.[0][0]).toMatchObject({ journal: "" });
});
