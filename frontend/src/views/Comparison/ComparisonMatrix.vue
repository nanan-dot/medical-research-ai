<script setup lang="ts">
import { computed } from "vue";
import ComparisonMatrixCell from "./ComparisonMatrixCell.vue";
import type { ComparisonField, ComparisonTask } from "../../types/comparison";

const props = defineProps<{ comparison: ComparisonTask; isSaving: boolean }>();
const emit = defineEmits<{ saveCell: [documentId: number, field: ComparisonField, userValue: string] }>();

const fieldLabels: Record<ComparisonField, string> = {
  study_type: "研究类型", study_population: "研究对象", sample_size: "样本量", intervention: "干预或暴露", comparator: "对照", outcome: "结局", methods: "研究方法", statistics: "统计方法", results: "主要结果", novelty: "创新点", limitations: "局限性", source: "来源",
};

const cellsByCoordinate = computed(() => new Map(props.comparison.cells.map((cell) => [`${cell.field}:${cell.document_id}`, cell])));

function cellFor(field: ComparisonField, documentId: number) {
  return cellsByCoordinate.value.get(`${field}:${documentId}`);
}
</script>

<template>
  <div class="table-wrap">
    <table class="comparison-matrix">
      <thead>
        <tr>
          <th scope="col">比较字段</th>
          <th v-for="documentId in comparison.selected_document_ids" :key="documentId" scope="col">文档 #{{ documentId }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="field in comparison.fields" :key="field">
          <th scope="row" :class="{ 'study-type-row': field === 'study_type' }">{{ fieldLabels[field] }}</th>
          <td v-for="documentId in comparison.selected_document_ids" :key="documentId">
            <ComparisonMatrixCell v-if="cellFor(field, documentId)" :cell="cellFor(field, documentId)!" :is-saving="isSaving" @save="emit('saveCell', documentId, field, $event)" />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-wrap { overflow: auto; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); }
.comparison-matrix { min-width: 940px; width: 100%; border-collapse: collapse; background: var(--paper); }
.comparison-matrix th, .comparison-matrix td { padding: .75rem; border-bottom: 1px solid var(--border-subtle); text-align: left; vertical-align: top; }
.comparison-matrix thead th { position: sticky; top: 0; z-index: 2; background: var(--surface-raised); color: var(--text-primary); }
.comparison-matrix tbody th { position: sticky; left: 0; z-index: 1; width: 130px; background: var(--paper); color: var(--text-primary); }
.comparison-matrix .study-type-row { color: var(--color-primary); }
</style>
