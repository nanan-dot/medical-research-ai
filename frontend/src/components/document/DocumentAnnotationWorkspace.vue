<script setup lang="ts">
import { shallowRef, useTemplateRef } from "vue";

import type { DocumentRecord } from "../../api/documents";
import type { AnnotationColor } from "../../api/documentAnnotations";
import { useDocumentAnnotations } from "../../composables/useDocumentAnnotations";
import type { PdfTextSelection } from "../../types/documentAnnotations";
import DocumentAnnotationEditor from "./DocumentAnnotationEditor.vue";
import DocumentAnnotationList from "./DocumentAnnotationList.vue";
import PdfAnnotationReader from "./PdfAnnotationReader.vue";

const props = defineProps<{
  document: DocumentRecord;
  sourceUrl: string;
}>();

const editor = useTemplateRef<InstanceType<typeof DocumentAnnotationEditor>>("editor");
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

function requestAnnotation(): void {
  editor.value?.focusNote();
}
</script>

<template>
  <section class="annotation-workspace" aria-label="PDF 划线与批注">
    <div class="reader-column">
      <PdfAnnotationReader
        :source-url="props.sourceUrl"
        :annotations="annotations"
        :selected-annotation-id="selectedAnnotationId"
        @selection-change="selection = $event"
        @request-annotation="requestAnnotation"
        @select-annotation="selectedAnnotationId = $event"
      />
    </div>
    <aside class="annotation-sidebar">
      <DocumentAnnotationEditor ref="editor" :selection="selection" :saving="saving" @submit="saveAnnotation" />
      <p v-if="loading" class="status" role="status">正在加载批注…</p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <DocumentAnnotationList
        :annotations="annotations"
        :selected-annotation-id="selectedAnnotationId"
        :disabled="saving"
        @select="selectedAnnotationId = $event"
        @remove="deleteAnnotation"
      />
    </aside>
  </section>
</template>

<style scoped>
.annotation-workspace { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(250px, .7fr); gap: 1rem; }
.reader-column, .annotation-sidebar { min-width: 0; }
.annotation-sidebar { display: grid; align-content: start; gap: .9rem; }
.status, .error { margin: 0; font-size: .84rem; }
.status { color: var(--text-muted); }.error { color: var(--color-danger); }
@media (max-width: 980px) { .annotation-workspace { grid-template-columns: 1fr; }.annotation-sidebar { grid-template-columns: repeat(2, minmax(0, 1fr)); align-items: start; } }
@media (max-width: 620px) { .annotation-sidebar { grid-template-columns: 1fr; } }
</style>
