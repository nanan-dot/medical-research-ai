import { apiRequest } from "./client";
import type { ChatAnswer, ChatCapabilities, ChatConversation, ChatRequest, ChatSummary, KnowledgeGap } from "../types/researchChat";
const ROOT = "/unified-conversations";
const json = (body: unknown): RequestInit => ({ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
export const researchChatApi = {
  capabilities: () => apiRequest<ChatCapabilities>(ROOT + "/capabilities"),
  list: () => apiRequest<ChatSummary[]>(ROOT),
  create: (documentIds: number[], title: string) => apiRequest<ChatConversation>(ROOT, json({ document_ids: documentIds, title })),
  get: (id: number) => apiRequest<ChatConversation>(ROOT + "/" + id),
  ask: (id: number, payload: ChatRequest, signal: AbortSignal) => apiRequest<ChatAnswer>(ROOT + "/" + id + "/messages", { ...json(payload), signal }),
  status: (id: number, requestId: string) => apiRequest<{ state: string; response: ChatAnswer | null }>(ROOT + "/" + id + "/requests/" + requestId),
  cancel: (id: number, requestId: string) => apiRequest<ChatAnswer>(ROOT + "/" + id + "/requests/" + requestId + "/cancel", { method: "POST" }),
  gaps: () => apiRequest<KnowledgeGap[]>(ROOT + "/gaps"),
  deleteGap: (id: number) => apiRequest<void>(ROOT + "/gaps/" + id, { method: "DELETE" }),
};
