<script setup lang="ts">
import type { MatrixCell } from "../../api/evidenceMatrices";
defineProps<{ cell: MatrixCell | null }>();
</script>

<template>
  <aside class="inspector">
    <p class="eyebrow">EVIDENCE CONTEXT</p><h2>{{ cell ? `文档 #${cell.document_id}` : "选择一个单元格" }}</h2>
    <template v-if="cell"><p class="status">状态：{{ cell.status === "user_edited" ? "人工修订" : cell.status === "generated" ? "已生成" : "缺失" }}</p><p v-if="cell.user_value" class="notice">此内容由人工修改，重新生成不会覆盖它。</p><a class="document-link" :href="`/documents/${cell.document_id}`">打开本地文档 #{{ cell.document_id }}</a><h3>来源</h3><ul v-if="cell.sources.length"><li v-for="source in cell.sources" :key="`${source.pmid}-${source.doi}-${source.locator}`">{{ source.pmid ? `PMID ${source.pmid}` : source.doi ? `DOI ${source.doi}` : "来源标识未提供" }}<small>定位：{{ source.locator || "未提供" }}</small><small>精确页码：未提供（矩阵来源未返回页码字段）</small></li></ul><p v-else>该单元格没有可验证来源，不能视为已生成证据。</p></template>
    <p v-else>选择表格中的内容以查看其状态、来源和人工修订信息。</p>
  </aside>
</template>

<style scoped>
.inspector{padding:1.35rem;border-left:1px solid var(--border-subtle);background:var(--surface-raised)}.eyebrow{margin:0;color:var(--color-primary);font-weight:850;font-size:.72rem;letter-spacing:.11em}.inspector h2{margin:.35rem 0;font-size:1.2rem}.inspector h3{margin:1.25rem 0 .45rem;font-size:.9rem}.inspector p,.inspector li{color:var(--text-muted);line-height:1.5}.status{font-weight:700}.notice{padding:.65rem;border-radius:7px;background:var(--color-primary-soft);color:var(--color-primary)!important}.document-link{display:inline-block;margin-top:.5rem;color:var(--color-primary);font-size:.85rem;font-weight:700}.inspector ul{display:grid;gap:.5rem;padding-left:1.1rem}.inspector small{display:block;margin-top:.15rem;color:var(--text-faint)}@media(max-width:900px){.inspector{border-left:0;border-top:1px solid var(--border-subtle)}}
</style>
