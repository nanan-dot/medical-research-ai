<script setup lang="ts">
import { shallowRef } from "vue";

import type { DocumentRecord } from "../../api/documents";
import type { AnnotationColor } from "../../api/documentAnnotations";
import { useDocumentAnnotations } from "../../composables/useDocumentAnnotations";
import type { PdfTextSelection } from "../../types/documentAnnotations";
import DocumentContextPanel from "./DocumentContextPanel.vue";
import PdfAnnotationReader from "./PdfAnnotationReader.vue";

const props = defineProps<{
  document: DocumentRecord;
  sourceUrl: string;
  summary: { page_count: number; character_count: number; section_headings: readonly string[] } | null;
  actionLoading: boolean;
}>();

const emit = defineEmits<{ retryParse: []; retryIndex: [] }>();

const selection = shallowRef<PdfTextSelection | null>(null);
const selectedAnnotationId = shallowRef<number | null>(null);
const { annotations, loading, saving, error, create, remove } = useDocumentAnnotations(
  props.document.id,
  () => props.document.file_hash,
);

async function saveAnnotation(payload: {
  selection: PdfTextSelection;
  color: AnnotationColor;
  note: string | null;
}): Promise<void> {
  const created = await create({
    page_number: payload.selection.pageNumber,
    rectangles: payload.selection.rectangles,
    selected_text: payload.selection.selectedText,
    color: payload.color,
    note: payload.note,
  });
  if (created) selection.value = null;
}

async function deleteAnnotation(annotationId: number): Promise<void> {
  if (await remove(annotationId) && selectedAnnotationId.value === annotationId) {
    selectedAnnotationId.value = null;
  }
}

function handleSelectionChange(nextSelection: PdfTextSelection | null): void {
  selection.value = nextSelection;
}

</script>

<template>
  <section class="annotation-workspace" aria-label="PDF 阅读与批注">
    <PdfAnnotationReader :source-url="props.sourceUrl" :annotations="annotations" :selected-annotation-id="selectedAnnotationId" @selection-change="handleSelectionChange" @select-annotation="selectedAnnotationId = $event" />
    <DocumentContextPanel :document="props.document" :summary="props.summary" :action-loading="props.actionLoading" :selection="selection" :annotations="annotations" :annotation-loading="loading" :annotation-saving="saving" :annotation-error="error" :selected-annotation-id="selectedAnnotationId" @retry-parse="emit('retryParse')" @retry-index="emit('retryIndex')" @save-annotation="saveAnnotation" @select-annotation="selectedAnnotationId = $event" @remove-annotation="deleteAnnotation" />
  </section>
</template>

<style scoped>
.annotation-workspace { display: grid; grid-template-columns: minmax(0, 1fr) clamp(320px, 25vw, 380px); align-items: start; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); overflow: hidden; background: var(--paper); }
.annotation-workspace > :first-child { min-width: 0; padding: 1rem; }
@media (max-width: 1024px) { .annotation-workspace { grid-template-columns: 1fr; }.annotation-workspace > :first-child { padding-bottom: 1rem; } }
</style>
