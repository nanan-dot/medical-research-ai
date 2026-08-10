import { readonly, shallowRef } from "vue";

import {
  documentsApi,
  type ContentSummary,
  type DocumentRecord,
} from "../api/documents";
import { documentPreviewsApi, type DocumentPreview } from "../api/documentPreviews";

export function useDocumentDetail(documentId: number) {
  const document = shallowRef<DocumentRecord | null>(null);
  const summary = shallowRef<ContentSummary | null>(null);
  const preview = shallowRef<DocumentPreview | null>(null);
  const loading = shallowRef(true);
  const previewLoading = shallowRef(false);
  const actionLoading = shallowRef(false);
  const error = shallowRef<string | null>(null);
  const previewError = shallowRef<string | null>(null);

  async function load(): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      const loadedDocument = await documentsApi.get(documentId);
      document.value = loadedDocument;
      await Promise.all([
        loadPreview(),
        loadSummary(loadedDocument),
      ]);
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : "无法加载文档";
    } finally {
      loading.value = false;
    }
  }

  async function retryParse(): Promise<void> {
    if (!document.value || actionLoading.value) return;
    actionLoading.value = true;
    try {
      if (document.value.parse_status === "failed") {
        await documentsApi.retryParse(document.value.id);
      }
      await documentsApi.parse(document.value.id);
      await load();
    } finally {
      actionLoading.value = false;
    }
  }

  async function retryIndex(): Promise<void> {
    if (!document.value || actionLoading.value) return;
    actionLoading.value = true;
    try {
      await documentsApi.retryIndex(document.value.id);
      await load();
    } finally {
      actionLoading.value = false;
    }
  }

  async function loadPreview(): Promise<void> {
    previewLoading.value = true;
    previewError.value = null;
    try {
      preview.value = await documentPreviewsApi.get(documentId);
    } catch (cause) {
      preview.value = null;
      previewError.value = cause instanceof Error ? cause.message : "无法加载原文预览";
    } finally {
      previewLoading.value = false;
    }
  }

  async function loadSummary(loadedDocument: DocumentRecord): Promise<void> {
    summary.value = loadedDocument.parse_status === "succeeded"
      ? await documentsApi.contentSummary(documentId)
      : null;
  }

  return {
    document: readonly(document),
    summary: readonly(summary),
    preview: readonly(preview),
    loading: readonly(loading),
    previewLoading: readonly(previewLoading),
    actionLoading: readonly(actionLoading),
    error: readonly(error),
    previewError: readonly(previewError),
    load,
    loadPreview,
    retryParse,
    retryIndex,
  };
}
