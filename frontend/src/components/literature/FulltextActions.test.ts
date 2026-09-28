import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, expect, test, vi } from "vitest";

import type { CitationItem, LibraryItem } from "../../api/literatureSearch";
import FulltextActions from "./FulltextActions.vue";

const { saveToLibrary, acquireOfficialPmcFulltext } = vi.hoisted(() => ({
  saveToLibrary: vi.fn(),
  acquireOfficialPmcFulltext: vi.fn(),
}));

vi.mock("../../api/literatureSearch", async (load) => ({
  ...await load<typeof import("../../api/literatureSearch")>(),
  literatureSearchApi: { saveToLibrary },
}));
vi.mock("../../api/openFulltext", () => ({ acquireOfficialPmcFulltext }));

const citation: CitationItem = {
  pmid: "123", pmcid: "PMC123", doi: "10.1000/example", title: "Paper", authors: [],
  journal: null, year: 2024, entry_type: "article", verified: true,
  verified_by: "pubmed", verified_on: "2026-08-26", has_abstract: false,
  abstract: null, publication_types: [],
};
const savedItem: LibraryItem = {
  id: 7, pmid: "123", pmcid: "PMC123", doi: citation.doi, title: "Paper", journal: null,
  year: 2024, document_id: null, source_search_id: 4, fulltext_status: "metadata_only",
  fulltext_status_reason: "metadata", created_at: "2026-08-26", updated_at: "2026-08-26",
};

beforeEach(() => {
  vi.clearAllMocks();
  saveToLibrary.mockResolvedValue(savedItem);
});

function mountActions(libraryItem: LibraryItem | null) {
  return mount(FulltextActions, {
    props: { resultId: 4, citation, libraryItem },
    global: { stubs: { RouterLink: { props: ["to"], template: '<a :href="to"><slot /></a>' } } },
  });
}

test("AC-FT-07 only calls PMC retrieval after the user activates the PMC action", async () => {
  acquireOfficialPmcFulltext.mockResolvedValue({
    item: { ...savedItem, document_id: 22, fulltext_status: "local_pdf_available" },
    acquisition: { status: "succeeded", license: "CC BY", document_id: 22 },
  });
  const wrapper = mountActions(null);
  expect(saveToLibrary).not.toHaveBeenCalled();
  expect(acquireOfficialPmcFulltext).not.toHaveBeenCalled();

  await wrapper.get('button[data-action="pmc"]').trigger("click");
  await flushPromises();

  expect(saveToLibrary).toHaveBeenCalledWith(4, "123");
  expect(acquireOfficialPmcFulltext).toHaveBeenCalledWith(7, "PMC123");
  expect(wrapper.text()).toContain("打开本地全文");
  expect(wrapper.emitted("updated")?.at(-1)?.[0]).toMatchObject({ document_id: 22 });
});

test("AC-FT-09 keeps PubMed available after an exact PMC failure", async () => {
  acquireOfficialPmcFulltext.mockRejectedValue(new Error("许可未验证"));
  const wrapper = mountActions(savedItem);

  await wrapper.get('button[data-action="pmc"]').trigger("click");
  await flushPromises();

  expect(wrapper.get('[role="alert"]').text()).toContain("许可未验证");
  expect(wrapper.get('a[href="https://pubmed.ncbi.nlm.nih.gov/123/"]').attributes("rel")).toBe("noopener noreferrer");
  expect(wrapper.find('input[type="file"]').exists()).toBe(false);
});

test("AC-FT-10 current results do not offer knowledge-base or local-PDF import actions", () => {
  const wrapper = mountActions(null);

  expect(wrapper.text()).not.toContain("加入知识库");
  expect(wrapper.text()).not.toContain("导入已下载PDF");
  expect(wrapper.find('input[type="file"]').exists()).toBe(false);
});

test("AC-FT-12 and AC-FT-15 expose only trusted external links and accessible status controls", () => {
  const wrapper = mountActions(null);
  const links = wrapper.findAll("a");
  expect(links.map((link) => link.attributes("href"))).toEqual([
    "https://pubmed.ncbi.nlm.nih.gov/123/",
    "https://doi.org/10.1000/example",
  ]);
  expect(wrapper.find('input[type="password"]').exists()).toBe(false);
  expect(wrapper.get('[aria-live="polite"]')).toBeTruthy();
});
