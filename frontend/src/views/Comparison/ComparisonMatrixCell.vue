<script setup lang="ts">
import { shallowRef, watch } from "vue";
import type { ComparisonCell } from "../../types/comparison";

const props = defineProps<{ cell: ComparisonCell; isSaving: boolean }>();
const emit = defineEmits<{ save: [userValue: string] }>();
const isEditing = shallowRef(false);
const draftValue = shallowRef(props.cell.cell_value);

const statusLabels = { generated: "已生成", user_edited: "人工修订", missing: "缺失" } as const;

watch(() => props.cell.cell_value, (value) => { draftValue.value = value; });

function save() {
  if (!draftValue.value.trim()) {
    return;
  }
  emit("save", draftValue.value);
  isEditing.value = false;
}

function sourceLabel(source: ComparisonCell["sources"][number]): string {
  return source.pmid ? `PMID ${source.pmid} · ${source.locator}` : `DOI ${source.doi} · ${source.locator}`;
}
</script>

<template>
  <div class="cell">
    <p class="cell-value">{{ cell.cell_value }}</p>
    <span class="status" :class="`status-${cell.status}`">{{ statusLabels[cell.status] }}</span>
    <ul v-if="cell.sources.length" class="sources" aria-label="单元格来源">
      <li v-for="source in cell.sources" :key="`${source.locator}-${source.pmid ?? source.doi}`">{{ sourceLabel(source) }}</li>
    </ul>
    <p v-else class="no-source">无可追溯来源</p>
    <button v-if="!isEditing" class="edit-button" :disabled="isSaving" @click="isEditing = true">人工修订</button>
    <form v-else class="edit-form" @submit.prevent="save">
      <label class="sr-only" :for="`cell-${cell.field}-${cell.document_id}`">人工修订 {{ cell.field }}</label>
      <textarea :id="`cell-${cell.field}-${cell.document_id}`" v-model="draftValue" :disabled="isSaving" rows="3" />
      <div class="edit-actions"><button type="submit" :disabled="isSaving">保存</button><button type="button" :disabled="isSaving" @click="isEditing = false">取消</button></div>
    </form>
  </div>
</template>

<style scoped>
.cell { display: grid; gap: .45rem; min-width: 190px; }
.cell-value, .no-source { margin: 0; overflow-wrap: anywhere; }
.cell-value { color: var(--text-primary); line-height: 1.5; }
.no-source { color: var(--text-faint); font-size: .78rem; }
.status { width: fit-content; padding: .18rem .45rem; border-radius: 99px; background: var(--surface-muted); color: var(--text-muted); font-size: .72rem; font-weight: 700; }
.status-generated { background: var(--color-success-soft); color: var(--color-success); }
.status-user_edited { background: var(--color-primary-soft); color: var(--color-primary); }
.status-missing { background: var(--color-warning-soft); color: var(--color-warning); }
.sources { display: grid; gap: .2rem; margin: 0; padding-left: 1rem; color: var(--text-muted); font-size: .75rem; overflow-wrap: anywhere; }
.edit-button, .edit-actions button { width: fit-content; padding: .35rem .55rem; border: 1px solid var(--border-strong); border-radius: 6px; background: var(--paper); color: var(--text-primary); font: inherit; font-size: .78rem; }
.edit-form { display: grid; gap: .4rem; }
.edit-form textarea { width: 100%; box-sizing: border-box; padding: .45rem; border: 1px solid var(--border-strong); border-radius: 6px; color: var(--text-primary); background: var(--paper); font: inherit; }
.edit-actions { display: flex; gap: .4rem; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
</style>
