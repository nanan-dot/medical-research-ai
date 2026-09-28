import { mount } from "@vue/test-utils";
import { expect, test } from "vitest";

import ResultsFilterSidebar from "./ResultsFilterSidebar.vue";

test("AC-14 only renders server-supported filters and applies facets without local filtering", async () => {
  const wrapper = mount(ResultsFilterSidebar, {
    props: {
      filters: { year: null, publication_type: "", journal: "", author: "", has_abstract: null, saved: null, read_status: "", tags: "", sort: "relevance" },
      facets: { year: { "2026": 12 }, publication_type: { Review: 8 } },
      filteredTotal: 20,
      disabled: false,
      open: true,
    },
  });

  expect(wrapper.text()).toContain("发表年份");
  expect(wrapper.text()).toContain("研究类型");
  expect(wrapper.text()).not.toContain("影响因子筛选");
  expect(wrapper.text()).not.toContain("被引次数筛选");
  await wrapper.get('input[value="Review"]').setValue(true);
  await wrapper.get('button[type="submit"]').trigger("click");
  expect(wrapper.emitted("apply")?.[0]?.[0]).toMatchObject({ publication_type: "Review" });
});

test("temporarily hides licensed JCR and WoS filters until authorized data is configured", () => {
  const wrapper = mount(ResultsFilterSidebar, { props: { filters: { year: null, publication_type: "", journal: "", author: "", has_abstract: null, saved: null, read_status: "", tags: "", sort: "relevance" }, facets: {}, filteredTotal: 0, disabled: false, open: true } });
  expect(wrapper.text()).not.toContain("JCR最佳分区");
  expect(wrapper.text()).not.toContain("WoS收录");
});

test("V2 applies the keyboard-accessible year range without scrolling to the submit button", async () => {
  const wrapper = mount(ResultsFilterSidebar, { props: { filters: { year: null, publication_type: "", journal: "", author: "", has_abstract: null, saved: null, read_status: "", tags: "", sort: "relevance" }, facets: {}, filteredTotal: 20, disabled: false, open: true } });
  const ranges = wrapper.findAll('input[type="range"]');
  await ranges[0].setValue("2022");
  await ranges[1].setValue("2025");
  await ranges[1].trigger("change");
  expect(wrapper.emitted("apply")?.at(-1)?.[0]).toMatchObject({ year_from: 2022, year_to: 2025 });
});

test("AC-FILTER-IMMEDIATE applies publication, journal, CAS and quick-year choices immediately", async () => {
  const wrapper = mount(ResultsFilterSidebar, { props: {
    filters: { year: null, year_from: null, year_to: null, publication_type: "", journal: "", author: "", has_abstract: null, saved: null, read_status: "", tags: "", sort: "relevance" },
    facets: { publication_type: { Review: 8 }, journal: { Nature: 4 }, cas: { "1区": 3 } }, filteredTotal: 20, disabled: false, open: true,
  } });

  await wrapper.get('input[value="Review"]').setValue(true);
  expect(wrapper.emitted("apply")?.at(-1)?.[0]).toMatchObject({ publication_type: "Review" });
  await wrapper.get('input[value="Nature"]').trigger("click");
  expect(wrapper.emitted("apply")?.at(-1)?.[0]).toMatchObject({ journal: "Nature" });
  await wrapper.findAll("button").find(button => button.text().includes("中科院分区"))!.trigger("click");
  await wrapper.get('input[name="cas"]').trigger("click");
  expect(wrapper.emitted("apply")?.at(-1)?.[0]).toMatchObject({ cas_quartile: "1区" });
  await wrapper.findAll("button").find(button => button.text()==="近3年")!.trigger("click");
  expect(wrapper.emitted("apply")?.at(-1)?.[0]).toMatchObject({ year_from: 2024, year_to: 2026 });
});

test("clicking an active single-choice facet again clears that filter", async () => {
  const wrapper = mount(ResultsFilterSidebar, { props: {
    filters: { year: null, year_from: null, year_to: null, publication_type: "", journal: "", author: "", has_abstract: null, saved: null, read_status: "", tags: "", sort: "relevance" },
    facets: { journal: { Nature: 4 } }, filteredTotal: 20, disabled: false, open: true,
  } });

  const journal = wrapper.get('input[value="Nature"]');
  await journal.trigger("click");
  expect(wrapper.emitted("apply")?.at(-1)?.[0]).toMatchObject({ journal: "Nature" });
  await journal.trigger("click");
  expect(wrapper.emitted("apply")?.at(-1)?.[0]).toMatchObject({ journal: "" });
});
