<script setup lang="ts">
import { shallowRef, useTemplateRef, watch } from "vue";

import type { DocumentRecord } from "../../api/documents";
import type { AnnotationColor } from "../../api/documentAnnotations";
import { useDocumentAnnotations } from "../../composables/useDocumentAnnotations";
import type { PdfTextSelection } from "../../types/documentAnnotations";
import type { VisibleReadingContext } from "../../types/readingContext";
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
const readingContext = shallowRef<VisibleReadingContext | null>(null);
const selectedAnnotationId = shallowRef<number | null>(null);
const noteConflictEpoch = shallowRef(0);
const reader = useTemplateRef<InstanceType<typeof PdfAnnotationReader>>("reader");
const { annotations, loading, saving, error, conflictEpoch, create, remove } = useDocumentAnnotations(
  () => props.document.id,
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
    anchor_descriptor: payload.selection.anchorDescriptor,
  });
  if (created) selection.value = null;
}

async function deleteAnnotation(annotationId: number): Promise<void> {
  if (await remove(annotationId) && selectedAnnotationId.value === annotationId) {
    selectedAnnotationId.value = null;
  }
}

function handleSelectionChange(nextSelection: PdfTextSelection | null): void {
  if (saving.value) return;
  selection.value = nextSelection;
}

function locateSourceAnchor(anchorId: number): void {
  void reader.value?.locateSourceAnchor(anchorId);
}

watch(() => [props.document.id, props.document.file_hash, conflictEpoch.value], () => {
  selection.value = null; selectedAnnotationId.value = null; readingContext.value = null;
});

</script>

<template>
  <section class="annotation-workspace" aria-label="PDF 阅读与批注">
    <PdfAnnotationReader ref="reader" :source-url="props.sourceUrl" :document-id="props.document.id" :file-hash="props.document.file_hash" :frozen="saving" :selection-epoch="conflictEpoch + noteConflictEpoch" :annotations="annotations" :selected-annotation-id="selectedAnnotationId" @selection-change="handleSelectionChange" @select-annotation="selectedAnnotationId = $event" @reading-context-change="readingContext = $event" />
    <DocumentContextPanel :document="props.document" :summary="props.summary" :action-loading="props.actionLoading" :selection="selection" :reading-context="readingContext" :annotations="annotations" :annotation-loading="loading" :annotation-saving="saving" :annotation-error="error" :selected-annotation-id="selectedAnnotationId" @retry-parse="emit('retryParse')" @retry-index="emit('retryIndex')" @save-annotation="saveAnnotation" @select-annotation="selectedAnnotationId = $event" @remove-annotation="deleteAnnotation" @revision-conflict="selection = null; noteConflictEpoch++" @locate-source-anchor="locateSourceAnchor" />
  </section>
</template>

<style scoped>
.annotation-workspace { display: grid; grid-template-columns: minmax(0, 1fr) clamp(320px, 25vw, 380px); align-items: start; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); overflow: hidden; background: var(--paper); }
.annotation-workspace > :first-child { min-width: 0; padding: 1rem; }
@media (max-width: 1024px) { .annotation-workspace { grid-template-columns: 1fr; }.annotation-workspace > :first-child { padding-bottom: 1rem; } }
</style>
