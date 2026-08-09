import { apiRequest } from "./client";

export type MatrixStatus = "draft" | "active" | "archived";
export type MatrixCellStatus = "generated" | "user_edited" | "missing";

export interface MatrixSource { pmid: string | null; doi: string | null; locator: string | null }
export interface MatrixField { id: number; matrix_id: number; field_key: string; field_label: string; position: number; active: boolean }
export interface MatrixDocument { id: number; matrix_id: number; document_id: number; user_notes: string; topic_relevance: "low"|"medium"|"high"; reading_status: "unread"|"reading"|"read"; document_status: "included"|"pending"; added_at: string }
export interface MatrixCell { id: number; matrix_id: number; document_id: number; field_key: string; cell_value: string; sources: MatrixSource[]; generated_value: string | null; user_value: string | null; status: MatrixCellStatus }
export interface EvidenceMatrix { id: number; name: string; description: string; status: MatrixStatus; version: number; source_comparison_id: number | null; created_at: string; updated_at: string; fields: MatrixField[]; documents: MatrixDocument[]; cells: MatrixCell[] }
export interface EvidenceMatrixPage { items: EvidenceMatrix[]; total: number }

export const evidenceMatricesApi = {
  list: () => apiRequest<EvidenceMatrixPage>("/evidence-matrices"),
  get: (matrixId: number) => apiRequest<EvidenceMatrix>(`/evidence-matrices/${matrixId}`),
  create: (name: string, description: string) => apiRequest<EvidenceMatrix>("/evidence-matrices", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, description }) }),
  updateCell: (matrixId: number, documentId: number, fieldKey: string, userValue: string) => apiRequest<EvidenceMatrix>(`/evidence-matrices/${matrixId}/cells`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ document_id: documentId, field_key: fieldKey, user_value: userValue }) }),
  regenerate: (matrixId: number) => apiRequest<EvidenceMatrix>(`/evidence-matrices/${matrixId}/regenerate`, { method: "POST" }),
};
