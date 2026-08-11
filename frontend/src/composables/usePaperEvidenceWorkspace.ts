import { computed, readonly, shallowRef, watch, type Ref } from "vue";

import { ApiError } from "../api/client";
import { conversationsApi, type Conversation, type ConversationSummary, type Message } from "../api/conversations";
import type { DocumentRecord } from "../api/documents";

function errorMessage(cause: unknown, fallback: string): string {
  return cause instanceof Error ? cause.message : fallback;
}

/** 论文切换时以请求序号隔离旧响应，避免较慢的上一论文请求覆盖当前工作台。 */
export function usePaperEvidenceWorkspace(document: Readonly<Ref<DocumentRecord | null>>, canCreate: Readonly<Ref<boolean>>) {
  const conversation = shallowRef<Conversation | null>(null);
  const history = shallowRef<readonly ConversationSummary[]>([]);
  const loading = shallowRef(false);
  const creating = shallowRef(false);
  const asking = shallowRef(false);
  const error = shallowRef<string | null>(null);
  let requestVersion = 0;

  const documentId = computed(() => document.value?.id ?? null);
  const documentHistory = computed(() => {
    const id = documentId.value;
    return id === null ? [] : history.value.filter((item) => item.document_ids.length === 1 && item.document_ids[0] === id);
  });
  const assistantMessages = computed(() => conversation.value?.messages.filter((message) => message.role === "assistant") ?? []);
  const latestAssistant = computed(() => assistantMessages.value.at(-1) ?? null);

  async function load(): Promise<void> {
    const id = documentId.value;
    const version = ++requestVersion;
    conversation.value = null;
    history.value = [];
    asking.value = false;
    error.value = null;
    if (id === null) return;
    loading.value = true;
    try {
      const [summaries, latest] = await Promise.all([
        conversationsApi.list(),
        conversationsApi.latest(id).catch((cause: unknown) => {
          if (cause instanceof ApiError && cause.status === 404) return null;
          throw cause;
        }),
      ]);
      if (version !== requestVersion) return;
      history.value = summaries;
      conversation.value = latest;
    } catch (cause) {
      if (version !== requestVersion) return;
      error.value = errorMessage(cause, "无法读取当前论文的问答会话。");
    } finally {
      if (version === requestVersion) loading.value = false;
    }
  }

  async function createConversation(): Promise<void> {
    const id = documentId.value;
    if (id === null || !canCreate.value || creating.value) return;
    const version = ++requestVersion;
    creating.value = true;
    error.value = null;
    try {
      const created = await conversationsApi.create([id]);
      if (version === requestVersion && documentId.value === id) {
        // 创建接口已返回完整会话；直接采用它可避免随后 latest 请求延迟时把成功状态误显示为空。
        conversation.value = created;
      }
    } catch (cause) {
      if (version === requestVersion) error.value = errorMessage(cause, "创建问答会话失败。");
    } finally {
      creating.value = false;
    }
  }

  async function openConversation(id: number): Promise<void> {
    if (asking.value) return;
    const documentAtRequest = documentId.value;
    const version = ++requestVersion;
    loading.value = true;
    error.value = null;
    try {
      const selected = await conversationsApi.get(id);
      if (version !== requestVersion || documentId.value !== documentAtRequest) return;
      if (documentAtRequest !== null && selected.document_ids.length === 1 && selected.document_ids[0] === documentAtRequest) conversation.value = selected;
    } catch (cause) {
      error.value = errorMessage(cause, "无法打开所选问答会话。");
    } finally {
      if (version === requestVersion) loading.value = false;
    }
  }

  async function ask(question: string): Promise<boolean> {
    const active = conversation.value;
    if (!active || asking.value || !question.trim()) return false;
    const version = ++requestVersion;
    const documentAtRequest = documentId.value;
    asking.value = true;
    error.value = null;
    try {
      await conversationsApi.ask(active.id, question.trim());
      // 服务端会同时持久化用户问题和回答；重新读取可避免用前端临时消息伪造会话历史。
      const refreshed = await conversationsApi.get(active.id);
      if (version !== requestVersion || documentId.value !== documentAtRequest || conversation.value?.id !== active.id) return false;
      conversation.value = refreshed;
      return true;
    } catch (cause) {
      error.value = errorMessage(cause, "问答请求失败，请重试。");
      return false;
    } finally {
      if (version === requestVersion) asking.value = false;
    }
  }

  async function feedback(message: Message, rating: 1 | -1): Promise<void> {
    const active = conversation.value;
    if (!active) return;
    error.value = null;
    try {
      const updated = await conversationsApi.feedback(active.id, message.id, rating);
      conversation.value = { ...active, messages: active.messages.map((item) => item.id === updated.id ? updated : item) };
    } catch (cause) {
      error.value = errorMessage(cause, "引用反馈提交失败，请重试。");
    }
  }

  watch(documentId, () => { void load(); }, { immediate: true });

  return { conversation: readonly(conversation), documentHistory, latestAssistant, loading: readonly(loading), creating: readonly(creating), asking: readonly(asking), error: readonly(error), load, createConversation, openConversation, ask, feedback };
}
