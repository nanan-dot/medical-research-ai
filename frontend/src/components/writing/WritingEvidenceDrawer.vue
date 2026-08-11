<script setup lang="ts">
import type { WritingEvidenceReference } from "../../api/writingProjects";

defineProps<{ reference: WritingEvidenceReference | null }>();
const emit = defineEmits<{ close: []; openDocument: [documentId: number] }>();
</script>

<template>
  <dialog :open="reference !== null" class="drawer" aria-label="证据定位">
    <template v-if="reference">
      <header class="header"><h2>证据定位</h2><button class="close" @click="emit('close')">关闭</button></header>
      <p><b>来源类型：</b>{{ reference.source_type }}</p>
      <p><b>页码：</b>{{ reference.page ?? "未提供" }}</p>
      <p><b>章节：</b>{{ reference.section || "未提供" }}</p>
      <p><b>PMID：</b>{{ reference.pmid || "未提供" }}</p>
      <p><b>DOI：</b>{{ reference.doi || "未提供" }}</p>
      <p><b>定位：</b>{{ reference.locator || "未提供" }}</p>
      <blockquote>{{ reference.evidence_text || "原文摘录未提供" }}</blockquote>
      <button v-if="reference.document_id" class="open-document" @click="emit('openDocument', reference.document_id)">
        打开本地文档
      </button>
      <p v-else class="unavailable">UNAVAILABLE：该引用没有可打开的本地文档。</p>
    </template>
  </dialog>
</template>

<style scoped>
.drawer{position:fixed;right:1rem;top:5rem;width:min(420px,calc(100vw - 2rem));border:1px solid var(--border-subtle);border-radius:var(--radius-md);padding:1rem;background:var(--paper);box-shadow:var(--shadow-card)}
.drawer::backdrop{background:rgba(16,33,61,.18)}.header{display:flex;align-items:center;justify-content:space-between;gap:1rem}.header h2{margin:0;font-size:1.15rem}.drawer p{color:var(--text-muted);line-height:1.5}.drawer blockquote{margin:1rem 0;padding:.75rem;border-left:3px solid var(--color-primary);background:var(--surface-muted);white-space:pre-wrap;line-height:1.55}.close,.open-document{border:0;border-radius:7px;padding:.5rem .7rem;background:var(--color-primary);color:#fff;font:inherit;cursor:pointer}.unavailable{padding:.65rem;background:var(--color-warning-soft)}
</style>
