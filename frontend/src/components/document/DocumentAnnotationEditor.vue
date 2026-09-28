<script setup lang="ts">
import { computed, shallowRef, useTemplateRef, watch } from "vue";

import type { AnnotationColor } from "../../api/documentAnnotations";
import type { PdfTextSelection } from "../../types/documentAnnotations";

const props = defineProps<{
  selection: PdfTextSelection | null;
  saving: boolean;
}>();

const emit = defineEmits<{
  submit: [payload: { selection: PdfTextSelection; color: AnnotationColor; note: string | null }];
}>();

const noteInput = useTemplateRef<HTMLTextAreaElement>("noteInput");
const color = shallowRef<AnnotationColor>("yellow");
const note = shallowRef("");
const frozenSelection = shallowRef<PdfTextSelection | null>(null);
const activeSelection = computed(() => frozenSelection.value ?? props.selection);

function submit(): void {
  if (!activeSelection.value || props.saving) return;
  emit("submit", {
    selection: activeSelection.value,
    color: color.value,
    note: note.value.trim() || null,
  });
}

function focusNote(): void {
  if (props.selection) frozenSelection.value = props.selection;
  noteInput.value?.focus();
}

watch(() => props.selection, (selection) => {
  if (!selection) frozenSelection.value = null;
  else if (!note.value) frozenSelection.value = selection;
});

defineExpose({ focusNote });
</script>

<template>
  <section class="annotation-editor" aria-labelledby="annotation-editor-title">
    <h3 id="annotation-editor-title" class="editor-title">添加批注</h3>
    <p v-if="activeSelection" class="selection-summary">
      第 {{ activeSelection.pageNumber }} 页：{{ activeSelection.selectedText }}
    </p>
    <p v-else class="selection-summary">请先在 PDF 文本层选中一段文字。</p>
    <label class="field-label">
      <span>高亮颜色</span>
      <select v-model="color" :disabled="props.saving || !props.selection">
        <option value="yellow">黄色</option>
        <option value="green">绿色</option>
        <option value="blue">蓝色</option>
        <option value="pink">粉色</option>
      </select>
    </label>
    <label class="field-label">
      <span>备注（可选）</span>
      <textarea ref="noteInput" v-model="note" :disabled="props.saving || !props.selection" maxlength="2000" rows="4" @focus="frozenSelection = activeSelection" />
    </label>
    <button class="save-button" :disabled="props.saving || !props.selection" @click="submit">
      {{ props.saving ? "正在保存…" : "保存批注" }}
    </button>
  </section>
</template>

<style scoped>
.annotation-editor { display: grid; gap: .65rem; padding: .9rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: var(--surface-muted); }
.editor-title { margin: 0; font-size: 1rem; }
.selection-summary { margin: 0; color: var(--text-muted); font-size: .84rem; line-height: 1.5; overflow-wrap: anywhere; }
.field-label { display: grid; gap: .3rem; color: var(--text-muted); font-size: .78rem; font-weight: 750; }
.field-label select, .field-label textarea { width: 100%; box-sizing: border-box; border: 1px solid var(--border-strong); border-radius: 7px; padding: .5rem; background: var(--paper); color: var(--text-primary); font: inherit; }
.save-button { justify-self: start; border: 0; border-radius: 7px; padding: .55rem .75rem; background: var(--color-primary); color: #fff; font: inherit; font-weight: 750; }
</style>
