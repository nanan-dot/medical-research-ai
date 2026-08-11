import { apiRequest } from "./client";

export interface IndexedPaper { document_id: number; title: string; year: number | null; pmid: string | null }
export interface IndexedPaperPage { items: IndexedPaper[]; total: number; offset: number; limit: number }
export interface RecentAnalysis { analysis_id: number; document_id: number; title: string; updated_at: string }
export interface PendingConfirmation { analysis_id: number; document_id: number; title: string; field_name: string; updated_at: string }
export interface RecentConversation { id: number; document_ids: readonly number[]; title: string | null; updated_at: string; message_count: number }
export interface PaperResearchOverview { recent_analyses: RecentAnalysis[]; pending_confirmations: PendingConfirmation[]; recent_conversations: RecentConversation[] }

export const paperResearchApi = {
  indexedDocuments(q = "", offset = 0, limit = 10): Promise<IndexedPaperPage> {
    const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
    if (q.trim()) params.set("q", q.trim());
    return apiRequest<IndexedPaperPage>(`/paper-research/indexed-documents?${params.toString()}`);
  },
  overview: (): Promise<PaperResearchOverview> => apiRequest<PaperResearchOverview>("/paper-research/overview"),
};
