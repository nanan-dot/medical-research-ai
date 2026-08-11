import { apiRequest } from "./client";

export interface ResearchContext {
  id: number;
  name: string;
  description: string;
  document_ids: number[];
  conversation_ids: number[];
  evidence_matrix_ids: number[];
  writing_project_ids: number[];
  literature_search_task_ids: number[];
  created_at: string;
  updated_at: string;
}

export const researchContextsApi = {
  list: () => apiRequest<ResearchContext[]>("/research-contexts"),
  create: (name: string, description = "") =>
    apiRequest<ResearchContext>("/research-contexts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description }),
    }),
  addDocuments: (contextId: number, documentIds: number[]) =>
    apiRequest<ResearchContext>(`/research-contexts/${contextId}/documents`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_ids: documentIds }),
    }),
};
