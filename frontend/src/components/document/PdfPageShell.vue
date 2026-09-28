<script setup lang="ts">
import { shallowRef } from "vue";
import type { AnnotationRect, DocumentAnnotation } from "../../api/documentAnnotations";

const props = defineProps<{
  pageNumber: number;
  width: number;
  height: number;
  error?: string;
  annotations: readonly { annotation: DocumentAnnotation; rect: AnnotationRect }[];
  selectionRectangles?: readonly AnnotationRect[];
  selectedAnnotationId: number | null;
}>();
const emit = defineEmits<{ retry: [page: number]; selectAnnotation: [id: number] }>();
const openAnnotationId = shallowRef<number | null>(null);
const colors: Record<DocumentAnnotation["color"], string> = {
  yellow: "rgba(246, 203, 73, .42)", green: "rgba(106, 190, 128, .38)",
  blue: "rgba(102, 164, 223, .38)", pink: "rgba(219, 123, 163, .38)",
};
function rectangleStyle(rect: AnnotationRect, color: DocumentAnnotation["color"]) {
  return { left: `${rect.left * 100}%`, top: `${rect.top * 100}%`, width: `${rect.width * 100}%`,
    height: `${rect.height * 100}%`, backgroundColor: colors[color] };
}
function selectionRectangleStyle(rect: AnnotationRect) {
  return {
    left: `${rect.left * 100}%`,
    top: `${rect.top * 100}%`,
    width: `${rect.width * 100}%`,
    height: `${rect.height * 100}%`,
  };
}
function toggleAnnotation(annotation: DocumentAnnotation): void {
  openAnnotationId.value = openAnnotationId.value === annotation.id ? null : annotation.id;
  emit("selectAnnotation", annotation.id);
}
</script>

<template>
  <div
    class="pdf-page"
    :data-page-number="pageNumber"
    :style="{ width: `${width}px`, height: `${height}px` }"
  >
    <div
      v-if="error"
      class="page-error"
      role="alert"
    >
      第 {{ pageNumber }} 页加载失败：{{ error }}
      <button @click="emit('retry', pageNumber)">重试此页</button>
    </div>
    <canvas
      class="pdf-canvas"
      aria-hidden="true"
    />
    <div
      class="text-layer"
      aria-label="可选择的 PDF 文本"
    />
    <div class="annotation-layer">
      <span
        v-for="(rect, index) in selectionRectangles ?? []"
        :key="`selection-${index}`"
        class="selection-highlight"
        :style="selectionRectangleStyle(rect)"
        aria-hidden="true"
      />
      <template v-for="(item, index) in annotations" :key="`${item.annotation.id}-${index}`">
      <button
        class="annotation-highlight"
        :class="{ 'annotation-highlight-selected': item.annotation.id === props.selectedAnnotationId }"
        :data-annotation-id="item.annotation.id"
        :style="rectangleStyle(item.rect, item.annotation.color)"
        :aria-label="item.annotation.note ? `查看笔记：${item.annotation.note}` : `定位高亮 ${item.annotation.id}`"
        :aria-expanded="item.annotation.note ? openAnnotationId === item.annotation.id : undefined"
        @click.stop="toggleAnnotation(item.annotation)"
      />
      <aside v-if="item.annotation.note && openAnnotationId === item.annotation.id" :key="`note-${item.annotation.id}`" class="annotation-note" role="note">
        <header><b>我的笔记</b><button type="button" aria-label="关闭笔记" @click.stop="openAnnotationId = null">×</button></header>
        <blockquote>{{ item.annotation.selected_text }}</blockquote>
        <p>{{ item.annotation.note }}</p>
      </aside>
      </template>
    </div>
  </div>
</template>

<style scoped>
.pdf-page { position: relative; box-shadow: var(--shadow-card); background: white; flex-shrink: 0; }
.pdf-canvas { display: block; }
.page-error { position: absolute; inset: 1rem; z-index: 2; color: var(--color-danger); background: var(--paper, white); }
.text-layer { position: absolute; inset: 0; overflow: hidden; line-height: 1; text-size-adjust: none; transform-origin: 0 0; }
.text-layer :deep(span), .text-layer :deep(br) { position: absolute; color: transparent; cursor: text; transform-origin: 0 0; }
.text-layer :deep(::selection) { background: rgba(57, 131, 212, .35); }
.annotation-layer { position: absolute; inset: 0; pointer-events: none; }
.selection-highlight { position: absolute; border-radius: 2px; background: rgba(57, 131, 212, .35); }
.annotation-highlight { position: absolute; border: 0; border-radius: 2px; pointer-events: auto; cursor: pointer; }
.annotation-highlight-selected { outline: 2px solid var(--color-primary); outline-offset: 1px; }
.annotation-highlight:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
.annotation-note { position:absolute;z-index:5;right:16px;bottom:16px;width:min(320px,calc(100% - 32px));box-sizing:border-box;padding:12px;border:1px solid #cbd7e8;border-radius:10px;background:#fff;box-shadow:0 12px 28px rgb(17 24 39 / 20%);color:#182235;pointer-events:auto; }
.annotation-note header { display:flex;align-items:center;justify-content:space-between; }
.annotation-note header button { width:28px;height:28px;border:0;border-radius:6px;background:#f1f5f9;color:#475467;font:inherit; }
.annotation-note blockquote { margin:9px 0;padding:7px 9px;border-left:3px solid #e8bd45;background:#fff9e8;color:#667085;font-size:11px;line-height:1.45; }
.annotation-note p { margin:0;font-size:13px;line-height:1.55;white-space:pre-wrap; }
</style>
