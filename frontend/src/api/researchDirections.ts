import { apiRequest } from "./client";

export type ConditionValue = string | number | string[] | null;
export interface ConditionField { value: ConditionValue; known: boolean; source: "user" | "unknown"; }
export interface ResearchConditionsPayload {
  specialty?: ConditionField;
  advisor_direction?: ConditionField;
  interest_topic?: ConditionField;
  existing_papers?: ConditionField;
  feasible_research_types?: ConditionField;
  sample_source?: ConditionField;
  technical_conditions?: ConditionField;
  data_resources?: ConditionField;
  timeline?: ConditionField;
  budget?: ConditionField;
  ethics_conditions?: ConditionField;
  uncertain_notes?: string;
}
export interface ResearchConditions extends ResearchConditionsPayload { id: number; conditions_version: number; created_at: string; updated_at: string; }
export interface SourceReference { document_id: number; locator: string; quote?: string | null; }
export interface GroundedText { text: string; sources: SourceReference[]; }
export interface EvidenceStatement { statement: string; source: SourceReference; }
export interface ResearchDirection {
  id: number; name: string; question: string; research_object: string; study_type: string;
  evidence: EvidenceStatement[]; current_evidence: GroundedText; controversy: GroundedText;
  gap: string; novelty_uncertainty: string; priority: "high" | "medium" | "low";
  missing_evidence: boolean; status: "active" | "merged" | "accepted" | "rejected";
  methods: string | null; requirements: string | null; difficulty: string | null;
  time_risk: string | null; resource_risk: string | null; ethics_risk: string | null;
  search_terms: string | null; advisor_questions: string | null;
}

export const researchDirectionsApi = {
  createConditions: (payload: ResearchConditionsPayload) => apiRequest<ResearchConditions>("/research-conditions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  generate: (researchConditionsId: number, evidenceMatrixId: number, candidateCount: number) => apiRequest<ResearchDirection[]>("/research-directions/generate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ research_conditions_id: researchConditionsId, evidence_matrix_id: evidenceMatrixId, candidate_count: candidateCount }) }),
  getDetails: (directionId: number) => apiRequest<ResearchDirection>(`/research-directions/${directionId}/details`),
  generateDetails: (directionId: number) => apiRequest<ResearchDirection>(`/research-directions/${directionId}/details`, { method: "POST" }),
};
