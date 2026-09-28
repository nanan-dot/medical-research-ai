import { readonly, shallowRef, watch } from "vue";

import {
  documentAnnotationsApi,
  type CreateDocumentAnnotation,
  type DocumentAnnotation,
  type UpdateDocumentAnnotation,
} from "../api/documentAnnotations";
import type { SourceAnchorDescriptor } from "../types/sourceAnchors";
import { ApiError } from "../api/client";

export function useDocumentAnnotations(documentId: number | (() => number), fileHash: () => string) {
  const currentId = () => typeof documentId === "number" ? documentId : documentId();
  const annotations = shallowRef<DocumentAnnotation[]>([]);
  const loading = shallowRef(false);
  const saving = shallowRef(false);
  const error = shallowRef<string | null>(null);
  const conflictEpoch = shallowRef(0);
  let generation = 0;
  let pendingKey = "";
  let pendingBody = "";

  async function load(): Promise<void> {
    const current = ++generation;
    loading.value = true;
    error.value = null;
    try {
      const result = await documentAnnotationsApi.list(currentId());
      if (current === generation) annotations.value = result;
    } catch (cause) {
      if (current === generation) error.value = cause instanceof Error ? cause.message : "无法加载批注";
    } finally {
      if (current === generation) loading.value = false;
    }
  }

  async function create(payload: Omit<CreateDocumentAnnotation, "expected_file_hash"> & { anchor_descriptor?: SourceAnchorDescriptor }): Promise<boolean> {
    if (saving.value) return false;
    saving.value = true;
    error.value = null;
    const capturedId = currentId(), capturedHash = fileHash();
    try {
      if (payload.anchor_descriptor) {
        const body = JSON.stringify([capturedId, payload]);
        if (pendingBody !== body) { pendingBody = body; pendingKey = crypto.randomUUID(); }
        await documentAnnotationsApi.createAnchored(capturedId, payload.anchor_descriptor, payload.color, payload.note, pendingKey);
        pendingBody = ""; pendingKey = "";
      } else await documentAnnotationsApi.create(capturedId, {
        ...payload,
        expected_file_hash: capturedHash,
      });
      if (capturedId !== currentId() || capturedHash !== fileHash()) return false;
      await load();
      return true;
    } catch (cause) {
      if (capturedId !== currentId() || capturedHash !== fileHash()) return false;
      if (cause instanceof ApiError && cause.code?.includes("REVISION_CONFLICT")) conflictEpoch.value++;
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
      await documentAnnotationsApi.update(currentId(), annotationId, {
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
      await documentAnnotationsApi.remove(currentId(), annotationId, fileHash());
      await load();
      return true;
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : "删除批注失败";
      return false;
    } finally {
      saving.value = false;
    }
  }

  watch(() => [currentId(), fileHash()], () => { annotations.value = []; void load(); }, { immediate: true });

  return {
    annotations: readonly(annotations),
    loading: readonly(loading),
    saving: readonly(saving),
    error: readonly(error),
    conflictEpoch: readonly(conflictEpoch),
    load,
    create,
    update,
    remove,
  };
}
