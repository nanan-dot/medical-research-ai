export type AgentTaskType = "evidence_qa" | "literature_search" | "research_direction" | "writing";
export interface AgentRun { run_id: string; workflow_status: string; decision?: string; approval_payload?: { task_type: string; evidence_status: string; limitations: string[]; actions: string[] }; }
export interface AgentTraceEvent { node: string; status: string; trace_id?: string; sources: Array<{ document_id: string; chunk_id: string; citation_id: string; page_number?: number }>; approval?: string; }
const BASE_URL = "/api/v1/agent";
async function request<T>(path: string, init?: RequestInit): Promise<T> { const response = await fetch(`${BASE_URL}${path}`, { headers: { "Content-Type": "application/json" }, ...init }); if (!response.ok) throw new Error((await response.json().catch(() => ({ detail: "请求失败" }))).detail); return response.json() as Promise<T>; }
export const startAgentRun = (query: string, taskType: AgentTaskType, publishRequested: boolean) => request<AgentRun>("/runs", { method: "POST", body: JSON.stringify({ query, task_type: taskType, publish_requested: publishRequested }) });
export const decideAgentRun = (runId: string, decision: "approve" | "reject") => request<AgentRun>(`/runs/${runId}/approve`, { method: "POST", body: JSON.stringify({ decision }) });
export const cancelAgentRun = (runId: string) => request<AgentRun>(`/runs/${runId}/cancel`, { method: "POST" });
export const getAgentTrace = (runId: string) => request<AgentTraceEvent[]>(`/runs/${runId}/trace`);
