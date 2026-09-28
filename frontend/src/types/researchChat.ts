export type ChatMode = "auto" | "general" | "evidence_only";
export interface ChatCitation {
  document_id: number | null; page: number | null; section: string | null;
  evidence_text: string | null; citation_text: string | null;
  source_anchor_id: number | null; anchor_status: string;
  url: string | null; pmid: string | null; source_level: "paper_excerpt" | "metadata" | "abstract";
}
export interface ChatSection { source_type: string; content: string; citations: ChatCitation[]; answer_status: string }
export interface ChatMessage {
  id: number; sequence: number; role: string; content: string; source_type: string;
  answer_status: string | null; created_at: string; sections: ChatSection[]; citations: ChatCitation[]; warnings: string[];
}
export interface ChatConversation { id: number; title: string | null; document_ids: number[]; research_context_id: number | null; messages: ChatMessage[] }
export interface ChatRequest {
  message: string; mode: ChatMode; document_ids: number[]; scope_type: "selected_documents";
  allow_general_supplement: boolean; allow_web_search: boolean; web_query: string | null; request_id: string;
}
export interface ChatAnswer {
  conversation_id: number; message_id: number; answer: string; answer_mode: string; answer_status: string;
  route_reason_code: string; scope_used: number[]; sections: ChatSection[]; citations: ChatCitation[];
  warnings: string[]; suggested_actions: string[]; trace_id: string; request_id: string; latency_ms: number;
}
export interface ChatCapabilities { migration_ready: boolean; full_library: boolean; streaming: boolean; selected_document_limit: number; external_source: string }
export interface KnowledgeGap { id: number; question: string; document_ids: number[]; research_context_id: number | null; occurrences: number }
export interface ChatSummary { id: number; title: string | null }
