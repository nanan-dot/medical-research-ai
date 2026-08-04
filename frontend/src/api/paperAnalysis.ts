export type ClaimKind = "fact" | "summary" | "inference" | "not_found";
export interface AnalysisField { value: string; kind: ClaimKind; source_indices: number[] }
export interface PaperSource {
  /** 后端来源 ID（真实字段），前端仅透传，不用于展示定位 */
  source_id?: string | number | null;
  /** 前端归一化来源序号，用于结构化字段的 source_indices 定位；后端不返回时按数组下标补齐 */
  local_index?: number;
  /** 原文摘录；后端未返回时展示"未提供" */
  excerpt?: string | null;
  /** 来源匹配得分；后端未返回时展示"未提供" */
  score?: number | null;
  citation: string | null;
  title: string | null;
  page_start: number | null;
  page_end: number | null;
}
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
