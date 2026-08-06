import { apiRequest } from "./client";
import type { ComparisonField, ComparisonTask } from "../types/comparison";

export function createComparison(selectedDocumentIds: number[]): Promise<ComparisonTask> {
  return apiRequest("/comparisons", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selected_document_ids: selectedDocumentIds }),
  });
}

export function getComparison(comparisonId: number): Promise<ComparisonTask> {
  return apiRequest(`/comparisons/${comparisonId}`);
}

export function updateComparisonCell(
  comparisonId: number,
  documentId: number,
  field: ComparisonField,
  userValue: string,
): Promise<ComparisonTask> {
  return apiRequest(`/comparisons/${comparisonId}/cells`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id: documentId, field, user_value: userValue }),
  });
}

export function regenerateComparison(comparisonId: number): Promise<ComparisonTask> {
  return apiRequest(`/comparisons/${comparisonId}/regenerate`, { method: "POST" });
}
