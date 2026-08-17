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
  await wrapper.get(".sort-control select").setValue("classic");

  expect(wrapper.emitted("apply")?.[0][0]).toMatchObject({ sort: "classic" });
  await wrapper.get(".sort-help summary").trigger("click");
  expect(wrapper.get(".sort-help").text()).toContain("不代表临床证据更强");
});

test("uses native accessible controls for sort and rationale disclosure", () => {
  const wrapper = mount(LiteratureFilters, { props: { filters, disabled: false } });
  expect(wrapper.get(".sort-control select").element.tagName).toBe("SELECT");
  expect(wrapper.get(".sort-help summary").element.tagName).toBe("SUMMARY");
});
