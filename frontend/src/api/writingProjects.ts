import { apiRequest } from "./client";

export type WritingType = "reading_note" | "group_meeting" | "review" | "proposal" | "introduction" | "discussion" | "abstract" | "cover_letter" | "reviewer_response";
export interface WritingSection { id: string; title: string; draft: string; }
export type EvidenceSourceType = "document" | "conversation_citation" | "matrix_cell";
export interface WritingEvidenceReference { id: number; segment_id: string; source_type: EvidenceSourceType; document_id: number | null; conversation_citation_id: number | null; matrix_cell_id: number | null; page: number | null; section: string | null; evidence_text: string | null; citation_text: string | null; pmid: string | null; doi: string | null; locator: string | null; }
export interface ContentSegment { id: string; text: string; origin: "user_provided" | "paper_evidence" | "model_summary" | "model_inference" | "pending"; citation_ids: string[]; pending_item_id: string | null; }
export interface GeneratedContent { sections: WritingSection[]; citations: Array<{ pmid: string | null; doi: string | null; locator: string | null }>; pending_items: Array<{ id: string; text: string; type: "citation" | "data" | "claim"; status: "pending" | "resolved"; section_id: string; paragraph_id: string }>; model_events: Array<{ model_name: string; model_version: string; generated_at: string; is_cloud: boolean }>; segments: ContentSegment[]; workflow_state: "drafting" | "outline_pending" | "outline_confirmed" | "user_editing" | "polishing" | "done"; }
export interface WritingProject { id: number; name: string; writing_type: WritingType; confidential: boolean; research_context_id: number | null; generated_content: GeneratedContent; version: number; user_materials: UserMaterial[]; evidence_references: WritingEvidenceReference[]; updated_at: string; }
export interface WritingVersion { version: number; parent_version: number | null; content: GeneratedContent; evidence_references: WritingEvidenceReference[]; created_at: string; }
export interface UserMaterial { id: number; text: string; source_document_id: number | null; }
export interface DisclosureDraft { id: number; project_id: number; content: string; version: number; }
const emptyContent = (): GeneratedContent => ({ sections: [{ id: "draft", title: "草稿", draft: "" }], citations: [], pending_items: [], model_events: [], segments: [], workflow_state: "drafting" });

export const writingProjectsApi = {
  list: () => apiRequest<WritingProject[]>("/writing-projects"),
  get: (projectId: number) => apiRequest<WritingProject>(`/writing-projects/${projectId}`),
  create: (name: string, writingType: WritingType, researchContextId: number | null) => apiRequest<WritingProject>("/writing-projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, writing_type: writingType, research_context_id: researchContextId, generated_content: emptyContent() }) }),
  updateContent: (project: WritingProject, content: GeneratedContent) => apiRequest<WritingProject>(`/writing-projects/${project.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ expected_version: project.version, generated_content: content }) }),
  addMaterial: (projectId: number, text: string) => apiRequest<UserMaterial>(`/writing-projects/${projectId}/materials`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) }),
  addDocumentEvidence: (projectId: number, segmentId: string, documentId: number) => apiRequest<WritingEvidenceReference>(`/writing-projects/${projectId}/evidence-references`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ segment_id: segmentId, source_type: "document", document_id: documentId }) }),
  saveVersion: (project: WritingProject) => apiRequest<WritingVersion>(`/writing-projects/${project.id}/versions?expected_version=${project.version}`, { method: "POST" }),
  listVersions: (projectId: number) => apiRequest<WritingVersion[]>(`/writing-projects/${projectId}/versions`),
  restoreVersion: (project: WritingProject, version: number) => apiRequest<WritingProject>(`/writing-projects/${project.id}/versions/${version}/restore?expected_version=${project.version}`, { method: "POST" }),
  submitOutline: (project: WritingProject, confirmed: boolean) => apiRequest<WritingProject>(`/writing-projects/${project.id}/outline`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: project.generated_content, expected_version: project.version, confirmed }) }),
  getDisclosure: (projectId: number) => apiRequest<DisclosureDraft>(`/ai-disclosure/projects/${projectId}/draft`),
  updateDisclosure: (draftId: number, content: string) => apiRequest<DisclosureDraft>(`/ai-disclosure/drafts/${draftId}?content=${encodeURIComponent(content)}`, { method: "PATCH" }),
};
