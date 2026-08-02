import { mount } from "@vue/test-utils";
import { expect, it } from "vitest";
import SearchTermsEditor from "./SearchTermsEditor.vue";

it("lets a user remove a synonym before building the query", async () => {
  const wrapper = mount(SearchTermsEditor, {
    props: {
      expanded: { term_groups: [{ name: "drug", core_term: "Aspirin", terms: ["aspirin", "ASA"], field_tag: "Title/Abstract", source: "curated_local_mapping" }], mesh_candidates: [], warnings: [], user_edits: {} },
      result: null,
      loading: false,
    },
  });

  await wrapper.find("input").setValue("aspirin");
  await wrapper.get("button").trigger("click");
  expect(wrapper.emitted("build")?.[0]?.[0]).toEqual([{ name: "drug", core_term: "Aspirin", terms: ["aspirin"], field_tag: "Title/Abstract", source: "curated_local_mapping" }]);
});
