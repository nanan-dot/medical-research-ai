import { apiRequest } from "./client";

export type WritingType = "reading_note" | "group_meeting" | "review" | "proposal" | "introduction" | "discussion" | "abstract" | "cover_letter" | "reviewer_response";
export interface WritingSection { id: string; title: string; draft: string; }
export interface GeneratedContent { sections: WritingSection[]; citations: unknown[]; pending_items: unknown[]; model_events: unknown[]; segments: unknown[]; workflow_state: "drafting" | "outline_pending" | "outline_confirmed" | "user_editing" | "polishing" | "done"; }
export interface WritingProject { id: number; name: string; writing_type: WritingType; confidential: boolean; generated_content: GeneratedContent; version: number; user_materials: UserMaterial[]; updated_at: string; }
export interface WritingVersion { version: number; parent_version: number | null; content: GeneratedContent; created_at: string; }
export interface UserMaterial { id: number; text: string; source_document_id: number | null; }
export interface DisclosureDraft { id: number; project_id: number; content: string; version: number; }
const emptyContent = (): GeneratedContent => ({ sections: [{ id: "draft", title: "草稿", draft: "" }], citations: [], pending_items: [], model_events: [], segments: [], workflow_state: "drafting" });

export const writingProjectsApi = {
  list: () => apiRequest<WritingProject[]>("/writing-projects"),
  get: (projectId: number) => apiRequest<WritingProject>(`/writing-projects/${projectId}`),
  create: (name: string, writingType: WritingType) => apiRequest<WritingProject>("/writing-projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, writing_type: writingType, generated_content: emptyContent() }) }),
  updateContent: (project: WritingProject, content: GeneratedContent) => apiRequest<WritingProject>(`/writing-projects/${project.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ expected_version: project.version, generated_content: content }) }),
  addMaterial: (projectId: number, text: string) => apiRequest<UserMaterial>(`/writing-projects/${projectId}/materials`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) }),
  saveVersion: (project: WritingProject) => apiRequest<WritingVersion>(`/writing-projects/${project.id}/versions?expected_version=${project.version}`, { method: "POST" }),
  listVersions: (projectId: number) => apiRequest<WritingVersion[]>(`/writing-projects/${projectId}/versions`),
  restoreVersion: (project: WritingProject, version: number) => apiRequest<WritingProject>(`/writing-projects/${project.id}/versions/${version}/restore?expected_version=${project.version}`, { method: "POST" }),
  submitOutline: (project: WritingProject, confirmed: boolean) => apiRequest<WritingProject>(`/writing-projects/${project.id}/outline`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: project.generated_content, expected_version: project.version, confirmed }) }),
  getDisclosure: (projectId: number) => apiRequest<DisclosureDraft>(`/ai-disclosure/projects/${projectId}/draft`),
  updateDisclosure: (draftId: number, content: string) => apiRequest<DisclosureDraft>(`/ai-disclosure/drafts/${draftId}?content=${encodeURIComponent(content)}`, { method: "PATCH" }),
};
