<script setup lang="ts">
import type { WritingEvidenceReference } from "../../api/writingProjects";

defineProps<{
  references: readonly WritingEvidenceReference[];
  contextDocumentIds: readonly number[];
  selectedSegmentId: string;
  isBusy: boolean;
}>();

const emit = defineEmits<{
  bindDocument: [documentId: number];
  openReference: [reference: WritingEvidenceReference];
}>();
</script>

<template>
  <aside class="evidence-panel" aria-label="写作证据">
    <p class="eyebrow">VERIFIED EVIDENCE</p>
    <h2 class="title">段落证据</h2>
    <p class="description">
      只能绑定当前研究上下文的本地文档。页码、章节和摘录仅在来源实际提供时显示。
    </p>
    <p v-if="!contextDocumentIds.length" class="empty">
      UNAVAILABLE：当前研究上下文没有关联文档，无法绑定证据。
    </p>
    <div v-else class="document-actions">
      <button
        v-for="documentId in contextDocumentIds"
        :key="documentId"
        class="document-button"
        :disabled="isBusy"
        @click="emit('bindDocument', documentId)"
      >
        为 {{ selectedSegmentId }} 绑定文档 #{{ documentId }}
      </button>
    </div>
    <ul v-if="references.length" class="reference-list">
      <li v-for="reference in references" :key="reference.id">
        <button class="reference-button" @click="emit('openReference', reference)">
          {{ reference.segment_id }} · {{ reference.citation_text || `文档 #${reference.document_id ?? "未提供"}` }}
        </button>
      </li>
    </ul>
    <p v-else class="empty">当前草稿尚未绑定可验证证据。</p>
  </aside>
</template>

<style scoped>
.evidence-panel{padding:1rem;border:1px solid var(--border-subtle);border-radius:var(--radius-md);background:var(--surface-raised)}
.eyebrow{margin:0;color:var(--color-primary);font-size:.72rem;font-weight:800;letter-spacing:.1em}
.title{margin:.35rem 0;font-size:1.05rem}.description,.empty{margin:.5rem 0;color:var(--text-muted);font-size:.85rem;line-height:1.55}
.document-actions,.reference-list{display:grid;gap:.45rem}.reference-list{margin:.8rem 0 0;padding:0;list-style:none}
.document-button,.reference-button{width:100%;border:1px solid var(--border-subtle);border-radius:7px;padding:.55rem;background:var(--paper);color:var(--color-primary);font:inherit;text-align:left;cursor:pointer}
.document-button:disabled{cursor:not-allowed;opacity:.6}
</style>
