import { computed, readonly, shallowRef, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { ApiError } from "../api/client";
import { conversationsApi, type Conversation } from "../api/conversations";
import { documentsApi, type DocumentRecord } from "../api/documents";
import { paperAnalysisApi, type PaperAnalysis } from "../api/paperAnalysis";

const DOCUMENT_PAGE_SIZE = 10;
const PDF_MEDIA_TYPES = new Set(["application/pdf", "application/x-pdf"]);

function queryDocumentId(value: unknown): number | null {
  if (typeof value !== "string") return null;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function isNotFoundError(cause: unknown): boolean {
  return cause instanceof ApiError && cause.status === 404;
}

export function isPdfDocument(document: DocumentRecord): boolean {
  return PDF_MEDIA_TYPES.has(document.media_type ?? "");
}

export function usePaperResearchWorkflow() {
  const route = useRoute();
  const router = useRouter();
  const searchQuery = shallowRef("");
  const researchReadyOnly = shallowRef(false);
  const previewableOnly = shallowRef(false);
  const offset = shallowRef(0);
  const documents = shallowRef<DocumentRecord[]>([]);
  const documentTotal = shallowRef(0);
  const documentsLoading = shallowRef(false);
  const documentsError = shallowRef<string | null>(null);
  const selectedDocument = shallowRef<DocumentRecord | null>(null);
  const analysis = shallowRef<PaperAnalysis | null>(null);
  const analysisLoading = shallowRef(false);
  const analysisError = shallowRef<string | null>(null);
  const conversation = shallowRef<Conversation | null>(null);
  const conversationLoading = shallowRef(false);
  const conversationError = shallowRef<string | null>(null);

  const currentDocumentId = computed(() => queryDocumentId(route.query.documentId));
  const canAnalyze = computed(() => {
    const document = selectedDocument.value;
    return document?.parse_status === "succeeded"
      && document.index_status === "succeeded"
      && Boolean(document.paperqa_index_key);
  });
  const canAnnotate = computed(() => selectedDocument.value ? isPdfDocument(selectedDocument.value) : false);

  async function loadDocuments(): Promise<void> {
    documentsLoading.value = true;
    documentsError.value = null;
    try {
      const page = await documentsApi.list(
        {
          parseStatus: "",
          indexStatus: "",
          query: searchQuery.value,
          researchReady: researchReadyOnly.value,
          previewableOnly: previewableOnly.value,
        },
        offset.value,
        DOCUMENT_PAGE_SIZE,
      );
      documents.value = page.items;
      documentTotal.value = page.total;
    } catch (cause) {
      documentsError.value = cause instanceof Error ? cause.message : "无法加载可选论文";
    } finally {
      documentsLoading.value = false;
    }
  }

  async function loadAnalysis(documentId: number): Promise<void> {
    analysisLoading.value = true;
    analysisError.value = null;
    try {
      analysis.value = await paperAnalysisApi.latest(documentId);
    } catch (cause) {
      if (isNotFoundError(cause)) {
        analysis.value = null;
        return;
      }
      analysis.value = null;
      analysisError.value = cause instanceof Error ? cause.message : "无法读取最近论文分析";
    } finally {
      analysisLoading.value = false;
    }
  }

  async function loadConversation(documentId: number): Promise<void> {
    conversationLoading.value = true;
    conversationError.value = null;
    try {
      conversation.value = await conversationsApi.latest(documentId);
    } catch (cause) {
      if (isNotFoundError(cause)) {
        conversation.value = null;
        return;
      }
      conversation.value = null;
      conversationError.value = cause instanceof Error ? cause.message : "无法读取最近单篇问答会话";
    } finally {
      conversationLoading.value = false;
    }
  }

  /** 切换论文时并行刷新两个只读资源，确保三个分区只围绕同一 document_id 展示。 */
  async function loadPaperContext(document: DocumentRecord): Promise<void> {
    selectedDocument.value = document;
    analysis.value = null;
    conversation.value = null;
    await Promise.all([loadAnalysis(document.id), loadConversation(document.id)]);
  }

  async function restoreDocument(documentId: number | null): Promise<void> {
    if (documentId === null) {
      selectedDocument.value = null;
      analysis.value = null;
      conversation.value = null;
      return;
    }
    const listedDocument = documents.value.find((item) => item.id === documentId);
    if (listedDocument) {
      await loadPaperContext(listedDocument);
      return;
    }
    try {
      await loadPaperContext(await documentsApi.get(documentId));
    } catch (cause) {
      selectedDocument.value = null;
      analysis.value = null;
      conversation.value = null;
      documentsError.value = cause instanceof Error ? cause.message : "当前论文不可用";
    }
  }

  async function selectDocument(document: DocumentRecord): Promise<void> {
    await router.replace({ query: { ...route.query, documentId: String(document.id) } });
  }

  function searchDocuments(): void {
    offset.value = 0;
    void loadDocuments();
  }

  function setResearchReadyOnly(value: boolean): void {
    researchReadyOnly.value = value;
    offset.value = 0;
    void loadDocuments();
  }

  function setPreviewableOnly(value: boolean): void {
    previewableOnly.value = value;
    offset.value = 0;
    void loadDocuments();
  }

  function changePage(nextOffset: number): void {
    offset.value = Math.max(0, nextOffset);
    void loadDocuments();
  }

  async function createAnalysis(): Promise<void> {
    if (!selectedDocument.value || !canAnalyze.value) return;
    analysisLoading.value = true;
    analysisError.value = null;
    try {
      analysis.value = await paperAnalysisApi.create(selectedDocument.value.id);
    } catch (cause) {
      analysisError.value = cause instanceof Error ? cause.message : "创建论文分析失败";
    } finally {
      analysisLoading.value = false;
    }
  }

  async function regenerateAnalysis(): Promise<void> {
    if (!analysis.value) return;
    analysisLoading.value = true;
    analysisError.value = null;
    try {
      analysis.value = await paperAnalysisApi.regenerate(analysis.value.id);
    } catch (cause) {
      analysisError.value = cause instanceof Error ? cause.message : "重新生成论文分析失败";
    } finally {
      analysisLoading.value = false;
    }
  }

  watch(currentDocumentId, (documentId) => {
    void restoreDocument(documentId);
  }, { immediate: true });

  void loadDocuments();

  return {
    searchQuery,
    researchReadyOnly,
    previewableOnly,
    offset: readonly(offset),
    pageSize: DOCUMENT_PAGE_SIZE,
    documents: readonly(documents),
    documentTotal: readonly(documentTotal),
    documentsLoading: readonly(documentsLoading),
    documentsError: readonly(documentsError),
    selectedDocument: readonly(selectedDocument),
    currentDocumentId,
    analysis: readonly(analysis),
    analysisLoading: readonly(analysisLoading),
    analysisError: readonly(analysisError),
    conversation: readonly(conversation),
    conversationLoading: readonly(conversationLoading),
    conversationError: readonly(conversationError),
    canAnalyze,
    canAnnotate,
    selectDocument,
    searchDocuments,
    setResearchReadyOnly,
    setPreviewableOnly,
    changePage,
    createAnalysis,
    regenerateAnalysis,
  };
}
