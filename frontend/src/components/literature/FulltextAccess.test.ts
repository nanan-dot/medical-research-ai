import { mount } from "@vue/test-utils";
import { expect, test } from "vitest";

import FulltextAccess from "./FulltextAccess.vue";

const routerStubs = { RouterLink: { props: ["to"], template: '<a :href="to"><slot /></a>' } };

test("links only a real local document and labels missing full text as restricted", () => {
  const available = mount(FulltextAccess, {
    props: { item: { id: 1, pmid: "1", pmcid: null, doi: null, title: null, journal: null, year: null, document_id: 42, source_search_id: 1, fulltext_status: "local_pdf_available", fulltext_status_reason: "Exact match", created_at: "2026-01-01", updated_at: "2026-01-01" } },
    global: { stubs: routerStubs },
  });
  expect(available.get('a[href="/documents/42"]').text()).toContain("查看本地全文");

  const restricted = mount(FulltextAccess, { props: { item: null }, global: { stubs: routerStubs } });
  expect(restricted.text()).toContain("全文获取受限");
  expect(restricted.find("a").exists()).toBe(false);
});

test("uses the returned PMC identifier only for an open-access full-text link", () => {
  const openAccess = mount(FulltextAccess, {
    props: { item: { id: 1, pmid: "1", pmcid: "PMC123", doi: null, title: null, journal: null, year: null, document_id: null, source_search_id: 1, fulltext_status: "open_access_available", fulltext_status_reason: "PMC", created_at: "2026-01-01", updated_at: "2026-01-01" } },
    global: { stubs: routerStubs },
  });
  const link = openAccess.get('a[href="https://pmc.ncbi.nlm.nih.gov/articles/PMC123/"]');
  expect(link.attributes("target")).toBe("_blank");
  expect(link.attributes("rel")).toBe("noopener noreferrer");
});
