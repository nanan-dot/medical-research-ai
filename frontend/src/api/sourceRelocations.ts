import { apiRequest } from "./client";
import type { AssetResolution, RelocationCandidate, ResolutionIssue } from "../types/sourceRelocations";

export const sourceRelocationsApi = {
  issues(documentId: number): Promise<ResolutionIssue[]> {
    return apiRequest(`/documents/${documentId}/anchor-resolution-issues`);
  },
  candidates(anchorId: number): Promise<RelocationCandidate[]> {
    return apiRequest(`/source-anchors/${anchorId}/relocation-candidates`);
  },
  generate(anchorId: number, targetAnchorRevisionId: number): Promise<RelocationCandidate[]> {
    return apiRequest(`/source-anchors/${anchorId}/relocation-candidates`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ target_anchor_revision_id: targetAnchorRevisionId }) });
  },
  decide(anchorId: number, issue: ResolutionIssue, candidateId: number, decision: "confirm" | "reject" | "supersede"): Promise<AssetResolution> {
    return apiRequest(`/source-anchors/${anchorId}/relocations/${candidateId}/decisions`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ asset_type: issue.asset_type, asset_id: issue.asset_id, candidate_id: candidateId, decision, expected_resolution_version: issue.resolution_version }) });
  },
};
