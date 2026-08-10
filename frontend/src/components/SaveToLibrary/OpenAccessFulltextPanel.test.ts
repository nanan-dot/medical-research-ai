import { mount } from "@vue/test-utils";
import { expect, test, vi } from "vitest";

import type { LibraryItem } from "../../api/literatureSearch";
import OpenAccessFulltextPanel from "./OpenAccessFulltextPanel.vue";

const { acquireOfficialPmcFulltext } = vi.hoisted(() => ({
  acquireOfficialPmcFulltext: vi.fn(),
}));

vi.mock("../../api/openFulltext", () => ({ acquireOfficialPmcFulltext }));

const item: LibraryItem = {
  id: 7,
  pmid: "123",
  pmcid: null,
  doi: "10.1000/example",
  title: "Example",
  journal: "Journal",
  year: 2026,
  document_id: null,
  source_search_id: 1,
  fulltext_status: "metadata_only",
  fulltext_status_reason: "No local PDF",
  created_at: "2026-08-10T00:00:00Z",
  updated_at: "2026-08-10T00:00:00Z",
};

test("enables acquisition only for a PMCID-shaped value", async () => {
  const wrapper = mount(OpenAccessFulltextPanel, {
    props: { item },
    global: { stubs: { RouterLink: true } },
  });

  const button = wrapper.get("button");
  expect(button.attributes("disabled")).toBeDefined();
  await wrapper.get("input").setValue("pmc123456");
  expect(button.attributes("disabled")).toBeUndefined();
});

test("shows official verification success and emits the updated item", async () => {
  const updated = { ...item, pmcid: "PMC123456", document_id: 12, fulltext_status: "local_pdf_available" as const };
  acquireOfficialPmcFulltext.mockResolvedValueOnce({
    item: updated,
    acquisition: {
      id: 3,
      library_item_id: 7,
      document_id: 12,
      pmcid: "PMC123456",
      status: "succeeded",
      source_url: "https://pmc.ncbi.nlm.nih.gov/api/oai/v1/mh/",
      license: "CC BY 4.0",
      file_format: "pdf",
      file_sha256: "a".repeat(64),
      error_code: null,
      error_message: null,
      attempted_at: "2026-08-10T00:00:00Z",
      retrieved_at: "2026-08-10T00:00:01Z",
    },
  });
  const wrapper = mount(OpenAccessFulltextPanel, {
    props: { item },
    global: { stubs: { RouterLink: true } },
  });

  await wrapper.get("input").setValue("PMC123456");
  await wrapper.get("button").trigger("click");
  await Promise.resolve();

  expect(acquireOfficialPmcFulltext).toHaveBeenCalledWith(7, "PMC123456");
  expect(wrapper.text()).toContain("CC BY 4.0");
  expect(wrapper.emitted("updated")?.[0]).toEqual([updated]);
});
