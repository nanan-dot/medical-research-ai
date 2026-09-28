import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { sourceAnchorsApi } from "../../api/sourceAnchors";
import { sourceRelocationsApi } from "../../api/sourceRelocations";
import AnchorRelocationReview from "./AnchorRelocationReview.vue";

vi.mock("../../api/sourceAnchors", () => ({ sourceAnchorsApi: { version: vi.fn(), get: vi.fn() } }));
vi.mock("../../api/sourceRelocations", () => ({ sourceRelocationsApi: { issues: vi.fn(), candidates: vi.fn(), generate: vi.fn(), decide: vi.fn() } }));

const issue = { asset_type: "document_annotation", asset_id: 4, original_anchor_id: 7,
  resolved_anchor_id: null, resolution_status: "relocation_required", resolution_version: 2, candidate_count: 1 };
const candidate = { id: 9, source_anchor_id: 7, target_anchor_revision_id: 3, candidate_anchor_id: 8,
  method: "quote_approximate", algorithm_version: "a3", score_breakdown: { quote_exactness: .91 },
  protected_token_status: "mismatch", status: "proposed", decision_source: null, created_at: "2026-08-31" };

beforeEach(() => {
  vi.mocked(sourceRelocationsApi.issues).mockResolvedValue([issue]);
  vi.mocked(sourceRelocationsApi.candidates).mockResolvedValue([candidate]);
  vi.mocked(sourceAnchorsApi.version).mockResolvedValue({ expected_file_hash: "a".repeat(64), expected_anchor_revision_id: 3, expected_segmentation_revision_id: 4 });
  vi.mocked(sourceAnchorsApi.get).mockImplementation(async id => ({ id, document_id: 1, anchor_revision_id: id === 7 ? 1 : 3,
    file_hash: "a".repeat(64), extraction_fingerprint: null, quote: id === 7 ? "Dose 5 mg" : "Dose 50 mg",
    quote_hash: "q".repeat(64), resolution_status: "exact", quality_status: "eligible", fragments: [], segment_ids: [], created_at: "2026-08-31" }));
});

describe("AnchorRelocationReview", () => {
  it("shows old/new evidence and blocks confirmation on protected-token mismatch", async () => {
    const wrapper = mount(AnchorRelocationReview, { props: { documentId: 1, fileHash: "a".repeat(64) } });
    await flushPromises(); await wrapper.get("button").trigger("click"); await flushPromises();
    expect(wrapper.text()).toContain("Dose 5 mg"); expect(wrapper.text()).toContain("Dose 50 mg");
    expect(wrapper.text()).toContain("保护表达：不一致，禁止确认");
    expect(wrapper.get("del").text()).toBe("");
    expect(wrapper.get("ins").text()).toBe("0");
    expect(wrapper.findAll("button").find(button => button.text() === "确认位置")?.attributes("disabled")).toBeDefined();
  });
});
