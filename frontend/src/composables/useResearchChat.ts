import { computed, onBeforeUnmount, ref, shallowRef } from "vue";
import { documentsApi, type DocumentRecord } from "../api/documents";
import { researchChatApi as api } from "../api/researchChat";
import { ApiError } from "../api/client";
import type { ChatAnswer, ChatCapabilities, ChatConversation, ChatMode, ChatRequest, ChatSummary, KnowledgeGap } from "../types/researchChat";

export function useResearchChat() {
  const capabilities = shallowRef<ChatCapabilities | null>(null);
  const conversation = shallowRef<ChatConversation | null>(null);
  const summaries = shallowRef<ChatSummary[]>([]);
  const documents = shallowRef<DocumentRecord[]>([]);
  const gaps = shallowRef<KnowledgeGap[]>([]);
  const selectedIds = ref<number[]>([]);
  const question = ref("");
  const mode = ref<ChatMode>("auto");
  const allowSupplement = ref(false);
  const allowWeb = ref(false);
  const webQuery = ref("");
  const isBusy = ref(false);
  const isLoading = ref(true);
  const error = ref("");
  const notice = ref("");
  const lastAnswer = shallowRef<ChatAnswer | null>(null);
  const pending = shallowRef<{ conversationId: number; payload: ChatRequest } | null>(null);
  let controller: AbortController | null = null;
  const canSend = computed(() => capabilities.value?.migration_ready && !pending.value && !isBusy.value && !isLoading.value && !!question.value.trim() && selectedIds.value.length <= 10);
  const describe = (cause: unknown) => cause instanceof Error ? cause.message : "请求未完成，请重试。";

  async function refresh(): Promise<void> {
    if (conversation.value) conversation.value = await api.get(conversation.value.id);
    const results = await Promise.allSettled([api.list(), api.gaps()]);
    if (results[0].status === "fulfilled") summaries.value = results[0].value;
    if (results[1].status === "fulfilled") gaps.value = results[1].value;
    if (results.some(result => result.status === "rejected")) notice.value = "部分历史或知识缺口未能刷新，可重新加载页面。";
  }
  async function initialize(): Promise<void> {
    isLoading.value = true;
    error.value = "";
    try {
      capabilities.value = await api.capabilities();
      if (!capabilities.value.migration_ready) return;
      await refresh();
      const page = await documentsApi.list({}, 0, 100);
      documents.value = page.items;
      if (page.total > page.items.length) notice.value = "当前显示最近 100 份资料，可通过资料搜索缩小范围。";
    } catch (cause) { error.value = describe(cause); }
    finally { isLoading.value = false; }
  }
  async function searchDocuments(query: string): Promise<void> {
    try { documents.value = (await documentsApi.list({ query }, 0, 100)).items; }
    catch (cause) { error.value = describe(cause); }
  }
  async function load(id: number): Promise<void> {
    if (isBusy.value || !id) return;
    isLoading.value = true;
    try {
      conversation.value = await api.get(id);
      selectedIds.value = [...conversation.value.document_ids];
      lastAnswer.value = null;
      pending.value = null;
      error.value = "";
    } catch (cause) { error.value = describe(cause); }
    finally { isLoading.value = false; }
  }
  function newConversation(): void {
    if (isBusy.value) return;
    conversation.value = null;
    lastAnswer.value = null;
    pending.value = null;
    error.value = "";
    question.value = "";
  }
  async function execute(payload: ChatRequest): Promise<void> {
    if (isBusy.value) return;
    isBusy.value = true;
    error.value = "";
    controller = new AbortController();
    try {
      if (!conversation.value) conversation.value = await api.create(selectedIds.value, payload.message.slice(0, 60));
      pending.value = { conversationId: conversation.value.id, payload };
      const answer = await api.ask(conversation.value.id, payload, controller.signal);
      lastAnswer.value = answer;
      pending.value = null;
      if (answer.answer_status === "answered") question.value = "";
    } catch (cause) {
      error.value = controller.signal.aborted ? "已停止等待，正在恢复已保存的请求状态。" : describe(cause);
    } finally {
      // 不确定的网络结果保留原请求编号，恢复时不会重复生成用户消息。
      try { await refresh(); } catch (cause) { notice.value = describe(cause); }
      isBusy.value = false;
      controller = null;
    }
  }
  async function send(): Promise<void> {
    if (!canSend.value) return;
    await execute({
      message: question.value.trim(), mode: mode.value, document_ids: [...selectedIds.value],
      scope_type: "selected_documents", allow_general_supplement: allowSupplement.value,
      allow_web_search: allowWeb.value, web_query: allowWeb.value ? webQuery.value.trim() || null : null,
      request_id: crypto.randomUUID(),
    });
  }
  async function recover(): Promise<void> {
    if (!pending.value || isBusy.value) return;
    const saved = pending.value;
    try {
      const state = await api.status(saved.conversationId, saved.payload.request_id);
      if (state.response) {
        lastAnswer.value = state.response;
        pending.value = null;
        error.value = "";
        await refresh();
      } else { notice.value = "请求仍在处理，可稍后恢复或取消。"; }
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 404) await execute(saved.payload);
      else error.value = describe(cause);
    }
  }
  async function cancel(): Promise<void> {
    const saved = pending.value;
    if (!saved) { controller?.abort(); return; }
    try {
      // 先确认服务器终态再中断等待，避免取消误报为成功。
      lastAnswer.value = await api.cancel(saved.conversationId, saved.payload.request_id);
      pending.value = null;
      controller?.abort();
      notice.value = lastAnswer.value.warnings.includes("cancelled") ? "请求已取消。" : "请求已完成，已恢复答案。";
      await refresh();
    } catch (cause) { error.value = describe(cause); }
  }
  async function deleteGap(id: number): Promise<void> {
    try { await api.deleteGap(id); gaps.value = gaps.value.filter(gap => gap.id !== id); }
    catch (cause) { error.value = describe(cause); }
  }
  onBeforeUnmount(() => controller?.abort());
  return { capabilities, conversation, summaries, documents, gaps, selectedIds, question, mode, allowSupplement, allowWeb, webQuery, isBusy, isLoading, error, notice, lastAnswer, pending, canSend, initialize, searchDocuments, load, newConversation, send, recover, cancel, deleteGap };
}
