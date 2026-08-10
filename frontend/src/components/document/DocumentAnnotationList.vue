<script setup lang="ts">
import type { DocumentAnnotation } from "../../api/documentAnnotations";

const props = defineProps<{
  annotations: readonly DocumentAnnotation[];
  selectedAnnotationId: number | null;
  disabled: boolean;
}>();

const emit = defineEmits<{
  select: [annotationId: number];
  remove: [annotationId: number];
}>();

function pageLabel(annotation: DocumentAnnotation): string {
  return `第 ${annotation.page_number} 页`;
}
</script>

<template>
  <section class="annotation-list" aria-labelledby="annotation-list-title">
    <h3 id="annotation-list-title" class="list-title">批注</h3>
    <p v-if="props.annotations.length === 0" class="empty-state">当前文档版本还没有批注。</p>
    <ul v-else class="items">
      <li v-for="annotation in props.annotations" :key="annotation.id" class="item">
        <button
          class="annotation-item"
          :class="{ 'annotation-item-selected': annotation.id === props.selectedAnnotationId }"
          :disabled="annotation.version_status !== 'current'"
          @click="emit('select', annotation.id)"
        >
          <span class="item-page">{{ pageLabel(annotation) }}</span>
          <span class="item-text">{{ annotation.selected_text }}</span>
          <span v-if="annotation.note" class="item-note">{{ annotation.note }}</span>
          <span v-if="annotation.version_status === 'relocation_required'" class="stale-state">需重新定位</span>
        </button>
        <button
          class="delete-button"
          :disabled="props.disabled || annotation.version_status !== 'current'"
          :aria-label="`删除批注 ${annotation.id}`"
          @click="emit('remove', annotation.id)"
        >
          删除
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.annotation-list { display: grid; gap: .65rem; }
.list-title { margin: 0; font-size: 1rem; }
.empty-state { margin: 0; color: var(--text-muted); font-size: .85rem; }
.items { display: grid; gap: .5rem; margin: 0; padding: 0; list-style: none; }
.item { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: .45rem; align-items: start; }
.annotation-item { display: grid; gap: .3rem; min-width: 0; border: 1px solid var(--border-subtle); border-radius: 8px; padding: .65rem; background: var(--paper); color: var(--text-primary); text-align: left; font: inherit; cursor: pointer; }
.annotation-item-selected { border-color: var(--color-primary); box-shadow: 0 0 0 1px var(--color-primary); }
.item-page, .stale-state { color: var(--text-muted); font-size: .74rem; font-weight: 800; }
.item-text, .item-note { overflow-wrap: anywhere; }
.item-note { color: var(--text-muted); font-size: .8rem; }
.stale-state { color: var(--color-warning); }
.delete-button { border: 0; padding: .45rem; background: transparent; color: var(--color-danger); font: inherit; font-size: .78rem; }
</style>
