import { describe, expect, it } from "vitest";
import { citationLink, sourceLabel } from "./chatLabels";
import type { ChatCitation } from "../../types/researchChat";
const citation: ChatCitation = { document_id: null, page: null, section: null, evidence_text: null, citation_text: null, source_anchor_id: null, anchor_status: "legacy_unversioned", url: "javascript:alert(1)", pmid: null, source_level: "metadata" };
describe("source links", () => {
  it("rejects untrusted URLs and malformed identifiers", () => {
    expect(citationLink(citation)).toBeNull();
    expect(citationLink({ ...citation, pmid: "../script" })).toBeNull();
    expect(citationLink({ ...citation, document_id: -1 })).toBeNull();
  });
  it("builds only scoped document and canonical PubMed links", () => {
    expect(citationLink({ ...citation, document_id: 2 })).toBe("/documents/2");
    expect(citationLink({ ...citation, pmid: "123" })).toBe("https://pubmed.ncbi.nlm.nih.gov/123/");
  });
  it("does not relabel legacy output as evidence", () => {
    expect(sourceLabel("legacy_unknown")).toContain("来源未标注");
    expect(sourceLabel("general")).toBe("模型通用回答");
  });
});
