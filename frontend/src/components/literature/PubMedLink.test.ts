import { mount } from "@vue/test-utils";
import { expect, test } from "vitest";

import PubMedLink from "./PubMedLink.vue";

test("AC-FT-12 only builds a fixed-host PubMed URL from a numeric PMID", () => {
  const valid = mount(PubMedLink, { props: { pmid: "12345" } });
  const invalid = mount(PubMedLink, { props: { pmid: "123/../../evil" } });

  expect(valid.get("a").attributes()).toMatchObject({
    href: "https://pubmed.ncbi.nlm.nih.gov/12345/",
    target: "_blank",
    rel: "noopener noreferrer",
  });
  expect(invalid.find("a").exists()).toBe(false);
});
