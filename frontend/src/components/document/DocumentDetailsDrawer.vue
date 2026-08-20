<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue";

import type { DocumentRecord } from "../../api/documents";
import DocumentInspector from "./DocumentInspector.vue";

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
let priorFocus: HTMLElement | null = null;

function close(): void {
  emit("close");
}

function trapFocus(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    close();
    return;
  }
  if (event.key !== "Tab" || !drawer.value) return;

  const focusable = [...drawer.value.querySelectorAll<HTMLElement>(
    'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
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

watch(() => props.document, async (document) => {
  if (document) {
    priorFocus = globalThis.document.activeElement instanceof HTMLElement
      ? globalThis.document.activeElement
      : null;
    globalThis.document.body.style.overflow = "hidden";
    await nextTick();
    drawer.value?.focus();
  } else {
    globalThis.document.body.style.overflow = "";
    await nextTick();
    priorFocus?.focus();
  }
});

onBeforeUnmount(() => {
  globalThis.document.body.style.overflow = "";
});
</script>

<template>
  <Teleport to="body">
    <div v-if="props.document" class="drawer-layer">
      <button class="backdrop" type="button" aria-label="关闭文档详情" @click="close" />
      <aside
        ref="drawer"
        class="drawer"
        role="dialog"
        aria-modal="true"
        aria-label="文档详情"
        tabindex="-1"
        @keydown="trapFocus"
      >
        <button class="close" type="button" aria-label="关闭文档详情" @click="close">×</button>
        <DocumentInspector
          :document="props.document"
          :disabled="props.disabled"
          :source-name="props.sourceName"
          :scope-name="props.scopeName"
          :total="props.total"
          @retry-index="emit('retryIndex', $event)"
          @retry-parse="emit('retryParse', $event)"
        />
      </aside>
    </div>
  </Teleport>
</template>

<style scoped>
.drawer-layer { position: fixed; z-index: 60; inset: 0; display: flex; justify-content: flex-end; }
.backdrop { position: absolute; inset: 0; border: 0; background: rgb(15 23 42 / 32%); }
.drawer { position: relative; width: min(460px, 100vw); height: 100%; overflow: auto; background: var(--surface); box-shadow: -12px 0 36px rgb(15 23 42 / 18%); }
.close { position: absolute; z-index: 1; top: 10px; right: 10px; width: 32px; height: 32px; border: 1px solid var(--border-subtle); border-radius: 7px; background: var(--surface); color: var(--text-muted); font-size: 1.25rem; cursor: pointer; }
.close:focus-visible, .backdrop:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
@media (prefers-reduced-motion: no-preference) { .drawer { animation: enter 160ms ease-out; } @keyframes enter { from { transform: translateX(20px); opacity: .6; } to { transform: translateX(0); opacity: 1; } } }
</style>
