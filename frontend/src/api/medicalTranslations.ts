import { apiRequest } from "./client";
import type { SourceAnchorDescriptor } from "../types/sourceAnchors";

export type TranslationJobState = "queued" | "running" | "quality_checking" | "succeeded" | "failed" | "cancelled";
export type TranslationQualityStatus = "machine_checked" | "needs_review" | "blocked" | "human_reviewed";

export interface TranslationJob {
  id: number;
  task_id: number;
  document_id: number;
  source_anchor_id: number;
  state: TranslationJobState;
  source_language: string;
  target_language: string;
  attempt_count: number;
  result_revision_id: number | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface TranslationIssue {
  code: string;
  severity: string;
  blocking: boolean;
  message: string;
  source_span: [number, number] | null;
  target_span: [number, number] | null;
}

export interface TranslationTerm {
  source_term: string;
  target_term: string | null;
  status: string;
  provenance: string;
  version: string;
  authority: string | null;
  source_span: [number, number] | null;
}

export interface TranslationRevision {
  id: number;
  document_id: number;
  source_anchor_id: number;
  version: number;
  origin: string;
  source_language: string;
  target_language: string;
  translated_text: string;
  alignment: Array<Record<string, unknown>>;
  terms: TranslationTerm[];
  issues: TranslationIssue[];
  quality_status: TranslationQualityStatus;
  provider: string;
  model: string;
  created_at: string;
}

export interface TranslationSegmentStatus {
  segment_id: number;
  translation_eligibility: string;
  state: "cached" | "queued" | "running" | "cooling_down" | "degraded";
  job: TranslationJob | null;
  revision: TranslationRevision | null;
  degraded_reason: string | null;
}

export interface TranslationPrefetchIntent {
  generation: string;
  items: TranslationSegmentStatus[];
  queued_count: number;
  deduplicated_count: number;
}

export const medicalTranslationsApi = {
  create(documentId: number, descriptor: SourceAnchorDescriptor, idempotencyKey: string): Promise<TranslationJob> {
    return apiRequest(`/documents/${documentId}/translation-jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({ anchor_descriptor: descriptor, source_language: "en", target_language: "zh-CN" }),
    });
  },
  requestSegments(documentId: number, payload: {
    expected_file_hash: string; expected_anchor_revision_id: number; expected_segmentation_revision_id: number;
    segment_ids: number[]; active_segment_id: number | null; trigger: "follow" | "visible" | "prefetch";
  }, signal?: AbortSignal): Promise<TranslationPrefetchIntent> {
    return apiRequest(`/documents/${documentId}/translation-segment-intents`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload), signal,
    });
  },
  job(jobId: number): Promise<TranslationJob> {
    return apiRequest(`/translation-jobs/${jobId}`);
  },
  cancel(jobId: number): Promise<TranslationJob> {
    return apiRequest(`/translation-jobs/${jobId}/cancel`, { method: "POST" });
  },
  retry(jobId: number): Promise<TranslationJob> {
    return apiRequest(`/translation-jobs/${jobId}/retry`, { method: "POST" });
  },
  revision(revisionId: number): Promise<TranslationRevision> {
    return apiRequest(`/translation-revisions/${revisionId}`);
  },
  correct(revisionId: number, expectedVersion: number, translatedText: string, reason: string | null): Promise<TranslationRevision> {
    return apiRequest(`/translation-revisions/${revisionId}/corrections`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expected_version: expectedVersion, translated_text: translatedText, reason }),
    });
  },
};
