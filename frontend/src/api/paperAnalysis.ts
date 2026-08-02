export type ClaimKind = "fact" | "summary" | "inference" | "not_found";
export interface AnalysisField { value: string; kind: ClaimKind; source_indices: number[] }
export interface PaperSource { citation: string | null; title: string | null; page_start: number | null; page_end: number | null }
export interface PaperAnalysis {
  id: number; document_id: number; analysis_status: "pending" | "analyzing" | "succeeded" | "failed";
  template_version: string; model_version: string; generation: number;
  structured_result: Record<string, AnalysisField> | null; sources: PaperSource[];
  pending_confirmations: string[]; error_code: string | null; error_message: string | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1/paper-analysis${path}`, init);
  if (!response.ok) throw new Error("论文分析请求失败");
  return (await response.json()) as T;
}

export const paperAnalysisApi = {
  create: (documentId: number) => request<PaperAnalysis>("", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ document_id: documentId }) }),
  get: (id: number) => request<PaperAnalysis>(`/${id}`),
  regenerate: (id: number) => request<PaperAnalysis>(`/${id}/regenerate`, { method: "POST" }),
  exportUrl: (id: number) => `/api/v1/paper-analysis/${id}/export`,
};
