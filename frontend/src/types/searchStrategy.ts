export type StrategySaveState = "unsaved" | "saving" | "saved" | "failed" | "conflict";

export interface SearchStrategyTerm {
  id: number;
  concept_group: string;
  text: string;
  source: "research_question" | "smart_expansion" | "user_added";
  field_tag: string | null;
  relation_type: string | null;
  is_locked: boolean;
  warning: { code: string; message: string; severity: string } | null;
}

export interface SearchStrategyMeshTerm {
  id: number;
  descriptor: string;
  mesh_id: string | null;
  concept_group: string;
  source: "nlm_mesh";
  verification_status: "verified" | "not_found" | "unavailable" | "stale";
  is_locked: boolean;
  verification_checked_at: string | null;
}

export interface StrategyValidation {
  is_syntax_valid: boolean;
  is_mesh_valid: boolean;
  are_field_tags_valid: boolean;
  warnings: Array<{ code: string; message: string; severity: string }>;
  blocking_errors: Array<{ code: string; message: string; severity: string }>;
  validated_fingerprint: string;
  validated_at: string;
}

export interface StrategyCount {
  count: number;
  fingerprint: string;
  retrieved_at: string;
  source: "pubmed";
}

export interface SearchStrategyVersion {
  id: number;
  strategy_id: number;
  version: number;
  fingerprint: string;
  note: string | null;
  created_at: string;
}

export interface StrategyVersionComparison {
  from_version: number;
  to_version: number;
  changes: Record<string, { from: unknown; to: unknown }>;
}

export interface SearchStrategyDraft {
  id: number;
  research_question: string;
  intent_mode: string;
  intent: Record<string, unknown>;
  limits: Record<string, unknown>;
  query_text: string;
  query_source: "generated" | "user_edited";
  fingerprint: string;
  revision: number;
  generation_state: string;
  validation_state: string;
  count_state: string;
  count: Record<string, unknown>;
  last_saved_at: string;
  terms: SearchStrategyTerm[];
  mesh_terms: SearchStrategyMeshTerm[];
}
