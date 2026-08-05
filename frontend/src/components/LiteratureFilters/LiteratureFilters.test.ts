import { mount } from "@vue/test-utils";
import { expect, test } from "vitest";

import type { ResultFilterValues } from "../../api/literatureSearch";
import LiteratureFilters from "./LiteratureFilters.vue";

const emptyFilters: ResultFilterValues = {
  year: null,
  publication_type: "",
  journal: "",
  author: "",
  has_abstract: null,
  saved: null,
  read_status: "",
  tags: "",
  sort: "relevance",
};

test("applies a combined filter set and resets filters", async () => {
  const wrapper = mount(LiteratureFilters, { props: { filters: emptyFilters, disabled: false } });

  await wrapper.get('input[placeholder="如 Nature Medicine"]').setValue("nature medicine");
  await wrapper.get('select').setValue("true");
  await wrapper.get('input[placeholder="如 Meta-Analysis"]').setValue("Meta-Analysis");
  await wrapper.get("form").trigger("submit");

  const applies = wrapper.emitted("apply");
  expect(applies?.at(-1)?.[0]).toEqual(
    expect.objectContaining({
      journal: "nature medicine",
      has_abstract: true,
      publication_type: "Meta-Analysis",
    }),
  );

  await wrapper.get('button[type="button"]').trigger("click");
  const resets = wrapper.emitted("apply");
  expect(resets?.at(-1)?.[0]).toEqual(
    expect.objectContaining({ journal: "", has_abstract: null, publication_type: "" }),
  );
});

test("keeps the sort choice across a reset", async () => {
  const wrapper = mount(LiteratureFilters, { props: { filters: emptyFilters, disabled: false } });
  const sortSelect = wrapper.findAll("select").at(-1)!;
  await sortSelect.setValue("classic");
  await wrapper.get('button[type="button"]').trigger("click");
  const resets = wrapper.emitted("apply");
  expect(resets?.at(-1)?.[0]).toEqual(expect.objectContaining({ sort: "classic" }));
});
