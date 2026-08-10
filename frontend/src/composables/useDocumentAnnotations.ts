import { readonly, shallowRef, watch } from "vue";

import {
  documentAnnotationsApi,
  type CreateDocumentAnnotation,
  type DocumentAnnotation,
  type UpdateDocumentAnnotation,
} from "../api/documentAnnotations";

export function useDocumentAnnotations(documentId: number, fileHash: () => string) {
  const annotations = shallowRef<DocumentAnnotation[]>([]);
  const loading = shallowRef(false);
  const saving = shallowRef(false);
  const error = shallowRef<string | null>(null);

  async function load(): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      annotations.value = await documentAnnotationsApi.list(documentId);
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : "无法加载批注";
    } finally {
      loading.value = false;
    }
  }

  async function create(payload: Omit<CreateDocumentAnnotation, "expected_file_hash">): Promise<boolean> {
    if (saving.value) return false;
    saving.value = true;
    error.value = null;
    try {
      await documentAnnotationsApi.create(documentId, {
        ...payload,
        expected_file_hash: fileHash(),
      });
      await load();
      return true;
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : "保存批注失败";
      return false;
    } finally {
      saving.value = false;
    }
  }

  async function update(
    annotationId: number,
    payload: Omit<UpdateDocumentAnnotation, "expected_file_hash">,
  ): Promise<boolean> {
    if (saving.value) return false;
    saving.value = true;
    error.value = null;
    try {
      await documentAnnotationsApi.update(documentId, annotationId, {
        ...payload,
        expected_file_hash: fileHash(),
      });
      await load();
      return true;
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : "更新批注失败";
      return false;
    } finally {
      saving.value = false;
    }
  }

  async function remove(annotationId: number): Promise<boolean> {
    if (saving.value) return false;
    saving.value = true;
    error.value = null;
    try {
      await documentAnnotationsApi.remove(documentId, annotationId, fileHash());
      await load();
      return true;
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : "删除批注失败";
      return false;
    } finally {
      saving.value = false;
    }
  }

  watch(fileHash, load, { immediate: true });

  return {
    annotations: readonly(annotations),
    loading: readonly(loading),
    saving: readonly(saving),
    error: readonly(error),
    load,
    create,
    update,
    remove,
  };
}
