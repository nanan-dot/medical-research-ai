<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue";

import type { DocumentRecord } from "../../api/documents";
import { documentPreviewsApi, type DocumentPreview } from "../../api/documentPreviews";
import DocumentInspector from "./DocumentInspector.vue";
import DocumentPreviewPanel from "./DocumentPreviewPanel.vue";

const props = defineProps<{
  document: DocumentRecord | null;
  disabled: boolean;
  sourceName: string | null;
  scopeName: string;
  total: number;
}>();

const emit = defineEmits<{
  close: [];
  retryIndex: [document: DocumentRecord];
  retryParse: [document: DocumentRecord];
}>();

const drawer = ref<HTMLElement | null>(null);
const drawerTitle = ref<HTMLElement | null>(null);
const preview = ref<DocumentPreview | null>(null);
const previewLoading = ref(false);
const previewError = ref<string | null>(null);
let priorFocus: HTMLElement | null = null;
let previewRequest = 0;

function close(): void {
  emit("close");
}

async function loadPreview(documentId: number): Promise<void> {
  const request = ++previewRequest;
  previewLoading.value = true;
  previewError.value = null;
  try {
    const loaded = await documentPreviewsApi.get(documentId);
    if (request === previewRequest) preview.value = loaded;
  } catch (cause) {
    if (request === previewRequest) {
      preview.value = null;
      previewError.value = cause instanceof Error ? cause.message : "无法加载资料预览";
    }
  } finally {
    if (request === previewRequest) previewLoading.value = false;
  }
}

function retryPreview(): void {
  if (props.document) void loadPreview(props.document.id);
}

function trapFocus(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    close();
    return;
  }
  if (event.key !== "Tab" || !drawer.value) return;

  const focusable = [...drawer.value.querySelectorAll<HTMLElement>(
    'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), iframe, [tabindex]:not([tabindex="-1"])',
  )];
  if (!focusable.length) {
    event.preventDefault();
    return;
  }

  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

function restoreFocusIfNeeded(): void {
  queueMicrotask(() => {
    if (props.document && drawer.value && !drawer.value.contains(globalThis.document.activeElement)) drawerTitle.value?.focus();
  });
}

watch(() => props.document, async (document, previousDocument) => {
  if (document) {
    preview.value = null;
    previewError.value = null;
    if (!previousDocument) {
      priorFocus = globalThis.document.activeElement instanceof HTMLElement
        ? globalThis.document.activeElement
        : null;
    }
    globalThis.document.body.style.overflow = "hidden";
    await nextTick();
    drawerTitle.value?.focus();
    void loadPreview(document.id);
  } else {
    previewRequest += 1;
    preview.value = null;
    previewError.value = null;
    previewLoading.value = false;
    globalThis.document.body.style.overflow = "";
    await nextTick();
    priorFocus?.focus();
    priorFocus = null;
  }
}, { immediate: true });

onBeforeUnmount(() => {
  previewRequest += 1;
  globalThis.document.body.style.overflow = "";
});
</script>

<template>
  <Teleport to="body">
    <div v-if="props.document" class="drawer-layer">
      <button class="backdrop" type="button" aria-label="关闭资料详情" @click="close" />
      <aside
        ref="drawer"
        class="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="resource-details-title"
        tabindex="-1"
        @keydown="trapFocus"
        @focusout="restoreFocusIfNeeded"
      >
        <h2 id="resource-details-title" ref="drawerTitle" class="sr-only" tabindex="-1">资料详情</h2>
        <button class="close" type="button" aria-label="关闭资料详情" @click="close">×</button>
        <DocumentInspector
          :document="props.document"
          :disabled="props.disabled"
          :source-name="props.sourceName"
          :scope-name="props.scopeName"
          :total="props.total"
          @retry-index="emit('retryIndex', $event)"
          @retry-parse="emit('retryParse', $event)"
        />
        <DocumentPreviewPanel
          class="drawer-preview"
          :preview="preview"
          :document="props.document"
          :loading="previewLoading"
          :error-message="previewError"
          @retry="retryPreview"
        />
      </aside>
    </div>
  </Teleport>
</template>

<style scoped>
.drawer-layer { position: fixed; z-index: 60; inset: 0; display: flex; justify-content: flex-end; }
.backdrop { position: absolute; inset: 0; border: 0; background: rgb(15 23 42 / 32%); }
.drawer { position: relative; width: min(600px, 100vw); height: 100%; overflow: auto; background: var(--surface); box-shadow: -12px 0 36px rgb(15 23 42 / 18%); }
.drawer-preview { padding: 0 16px 16px; }
.close { position: absolute; z-index: 1; top: 10px; right: 10px; width: 32px; height: 32px; border: 1px solid var(--border-subtle); border-radius: 7px; background: var(--surface); color: var(--text-muted); font-size: 1.25rem; cursor: pointer; }
.close:focus-visible, .backdrop:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
.sr-only { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; }
@media (prefers-reduced-motion: no-preference) { .drawer { animation: enter 160ms ease-out; } @keyframes enter { from { transform: translateX(20px); opacity: .6; } to { transform: translateX(0); opacity: 1; } } }
</style>
