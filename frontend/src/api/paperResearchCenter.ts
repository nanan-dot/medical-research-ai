import { apiRequest } from "./client";

export type ResearchStage = "problem_definition" | "literature_reading" | "paper_understanding" | "evidence_organization" | "conclusion_formation";
export interface CenterCurrentResearch { research_context_id: number | null; research_name: string | null; stage: ResearchStage; version: number }
export interface CenterNextAction { kind: string; title: string; description: string; reason_codes: string[]; target: Record<string, unknown> | null; is_available: boolean; unavailable_reason: string | null }
export interface CenterTask { paper_item_id: number; title: string | null; journal: string | null; year: number | null; work_mode: string; current_section: string | null; reading_progress_percent: number; analysis_completed: number; analysis_total: number; last_work_at: string | null; entry_available: boolean; next_action: CenterNextAction; sort_reason: string }
export interface CenterActivity { id: number; kind: string; occurred_at: string; paper_item_id: number; paper_title: string | null; research_context_id: number | null; research_name: string | null; target: Record<string, unknown> | null; summary: string | null; target_available: boolean; unavailable_reason: string | null }
export interface CenterPaper { paper_item_id: number; title: string | null; journal: string | null; year: number | null; reading_status: string; entry_available: boolean; last_work_at: string | null }
export interface CenterSummary { papers: number; reading: number; deep_reading: number; completed: number; pending_confirmation_items: number; pending_confirmation_fields: number }
export interface PaperCenterData { current_research: CenterCurrentResearch | null; continue_tasks: CenterTask[]; recent_activities: CenterActivity[]; recent_papers: CenterPaper[]; summary: CenterSummary; capabilities: Record<string, string> }
export const paperResearchCenterApi = { center: (signal?: AbortSignal) => apiRequest<PaperCenterData>("/paper-research/center", { signal }) };
