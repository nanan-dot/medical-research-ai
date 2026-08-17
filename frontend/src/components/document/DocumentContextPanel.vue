<script setup lang="ts">
import { shallowRef, useTemplateRef } from "vue";

import type { DocumentRecord } from "../../api/documents";
import DocumentAnnotationEditor from "./DocumentAnnotationEditor.vue";
import DocumentAnnotationList from "./DocumentAnnotationList.vue";
import DocumentDetailOverview from "./DocumentDetailOverview.vue";
import type { AnnotationColor, DocumentAnnotation } from "../../api/documentAnnotations";
import type { PdfTextSelection } from "../../types/documentAnnotations";

const props = defineProps<{
  document: DocumentRecord;
  summary: { page_count: number; character_count: number; section_headings: readonly string[] } | null;
  actionLoading: boolean;
  selection: PdfTextSelection | null;
  annotations: readonly DocumentAnnotation[];
  annotationLoading: boolean;
  annotationSaving: boolean;
  annotationError: string | null;
  selectedAnnotationId: number | null;
}>();

const emit = defineEmits<{
  retryParse: [];
  retryIndex: [];
  saveAnnotation: [payload: { selection: PdfTextSelection; color: AnnotationColor; note: string | null }];
  selectAnnotation: [annotationId: number];
  removeAnnotation: [annotationId: number];
}>();

const activeTab = shallowRef<"information" | "annotations">("information");
const tabButtons = useTemplateRef<HTMLButtonElement[]>("tabButtons");
const editor = useTemplateRef<InstanceType<typeof DocumentAnnotationEditor>>("editor");
const tabIds = ["information", "annotations"] as const;

function selectTab(tab: "information" | "annotations", focus = false): void {
  activeTab.value = tab;
  if (tab === "annotations") window.setTimeout(() => editor.value?.focusNote(), 0);
  if (focus) tabButtons.value?.[tabIds.indexOf(tab)]?.focus();
}

function handleTabKeydown(event: KeyboardEvent, currentTab: "information" | "annotations"): void {
  const currentIndex = tabIds.indexOf(currentTab);
  const nextIndex = event.key === "ArrowRight" ? (currentIndex + 1) % tabIds.length
    : event.key === "ArrowLeft" ? (currentIndex - 1 + tabIds.length) % tabIds.length
      : event.key === "Home" ? 0 : event.key === "End" ? tabIds.length - 1 : null;
  if (nextIndex === null) return;
  event.preventDefault();
  selectTab(tabIds[nextIndex], true);
}
</script>

<template>
  <aside class="context-panel" aria-label="文档上下文">
    <div class="tab-list" role="tablist" aria-label="文档上下文选项">
      <button ref="tabButtons" class="tab" type="button" role="tab" aria-controls="document-information-panel" :aria-selected="activeTab === 'information'" :tabindex="activeTab === 'information' ? 0 : -1" @click="selectTab('information')" @keydown="handleTabKeydown($event, 'information')">文档信息</button>
      <button ref="tabButtons" class="tab" type="button" role="tab" aria-controls="document-annotations-panel" :aria-selected="activeTab === 'annotations'" :tabindex="activeTab === 'annotations' ? 0 : -1" @click="selectTab('annotations')" @keydown="handleTabKeydown($event, 'annotations')">批注</button>
    </div>
    <div v-if="activeTab === 'information'" id="document-information-panel" class="tab-panel" role="tabpanel" aria-label="文档信息">
      <DocumentDetailOverview :document="props.document" :summary="props.summary" :action-loading="props.actionLoading" @retry-parse="emit('retryParse')" @retry-index="emit('retryIndex')" />
    </div>
    <div v-else id="document-annotations-panel" class="tab-panel" role="tabpanel" aria-label="批注">
      <DocumentAnnotationEditor ref="editor" :selection="props.selection" :saving="props.annotationSaving" @submit="emit('saveAnnotation', $event)" />
      <p v-if="props.annotationLoading" class="status" role="status" aria-live="polite">正在加载批注。</p>
      <p v-if="props.annotationError" class="error" role="alert">{{ props.annotationError }}</p>
      <DocumentAnnotationList :annotations="props.annotations" :selected-annotation-id="props.selectedAnnotationId" :disabled="props.annotationSaving" @select="emit('selectAnnotation', $event)" @remove="emit('removeAnnotation', $event)" />
    </div>
  </aside>
</template>

<style scoped>
.context-panel { min-width: 0; border-left: 1px solid var(--border-subtle); background: var(--paper); }
.tab-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); border-bottom: 1px solid var(--border-subtle); }
.tab { border: 0; border-bottom: 2px solid transparent; padding: .85rem .7rem .7rem; background: transparent; color: var(--text-muted); font: inherit; font-size: .88rem; font-weight: 750; cursor: pointer; }
.tab[aria-selected="true"] { border-bottom-color: var(--color-primary); color: var(--color-primary); }
.tab:focus-visible, .context-panel :deep(button:focus-visible) { outline: 3px solid color-mix(in srgb, var(--color-primary) 45%, transparent); outline-offset: -3px; }
.tab-panel { display: grid; align-content: start; gap: .9rem; padding: 1rem; }
.status, .error { margin: 0; font-size: .84rem; }.status { color: var(--text-muted); }.error { color: var(--color-danger); }
@media (max-width: 1024px) { .context-panel { border-top: 1px solid var(--border-subtle); border-left: 0; } }
</style>
