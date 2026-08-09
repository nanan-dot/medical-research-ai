<script setup lang="ts">
import { computed, shallowRef } from "vue";
import type { EvidenceMatrix, MatrixCell, MatrixField } from "../../api/evidenceMatrices";

const props = defineProps<{ matrix: EvidenceMatrix; saving: boolean }>();
const emit = defineEmits<{ selectCell: [cell: MatrixCell]; saveCell: [documentId: number, fieldKey: string, value: string] }>();
const drafts = shallowRef<Record<string, string>>({});
const rows = computed(() => [...props.matrix.fields].sort((left, right) => left.position - right.position));

function cellFor(field: MatrixField, documentId: number): MatrixCell | undefined { return props.matrix.cells.find((cell) => cell.field_key === field.field_key && cell.document_id === documentId); }
function draftKey(fieldKey: string, documentId: number): string { return `${fieldKey}:${documentId}`; }
function valueFor(cell: MatrixCell | undefined): string { return cell?.cell_value ?? "缺失"; }
function setDraft(key: string, value: string): void { drafts.value = { ...drafts.value, [key]: value }; }
function save(field: MatrixField, documentId: number, cell: MatrixCell | undefined): void { const value = drafts.value[draftKey(field.field_key, documentId)] ?? cell?.cell_value; if (value?.trim()) emit("saveCell", documentId, field.field_key, value.trim()); }
</script>

<template>
  <div class="table-scroll">
    <table class="matrix-table">
      <thead><tr><th class="field-heading">证据维度</th><th v-for="document in matrix.documents" :key="document.document_id">文档 #{{ document.document_id }}</th></tr></thead>
      <tbody><tr v-for="field in rows" :key="field.id"><th class="field-label">{{ field.field_label }}</th><td v-for="document in matrix.documents" :key="document.document_id"><template v-if="cellFor(field, document.document_id)"><button class="cell-value" :class="cellFor(field, document.document_id)?.status" @click="emit('selectCell', cellFor(field, document.document_id)!)">{{ valueFor(cellFor(field, document.document_id)) }}</button><textarea :value="drafts[draftKey(field.field_key, document.document_id)] ?? cellFor(field, document.document_id)?.cell_value" :disabled="saving" aria-label="编辑证据单元格" @input="setDraft(draftKey(field.field_key, document.document_id), ($event.target as HTMLTextAreaElement).value)" @blur="save(field, document.document_id, cellFor(field, document.document_id))" /></template><span v-else class="missing">缺失</span></td></tr></tbody>
    </table>
  </div>
</template>

<style scoped>
.table-scroll{overflow:auto;border:1px solid var(--border-subtle);border-radius:var(--radius-md);background:var(--paper)}.matrix-table{min-width:860px;width:100%;border-collapse:collapse}.matrix-table th,.matrix-table td{padding:.75rem;border-bottom:1px solid var(--border-subtle);text-align:left;vertical-align:top}.matrix-table thead th{position:sticky;top:0;background:var(--surface-raised);z-index:1}.field-heading,.field-label{min-width:150px}.field-label{position:sticky;left:0;background:var(--paper);z-index:1}.cell-value{display:block;width:100%;min-height:42px;border:0;background:transparent;text-align:left;font:inherit;line-height:1.45;cursor:pointer}.cell-value.generated{color:var(--text-primary)}.cell-value.user_edited{color:var(--color-primary);font-weight:700}.cell-value.missing,.missing{color:var(--text-muted)}textarea{width:100%;min-height:54px;margin-top:.5rem;padding:.4rem;border:1px solid var(--border-subtle);border-radius:6px;background:var(--surface-muted);font:inherit;font-size:.82rem;resize:vertical}
</style>
