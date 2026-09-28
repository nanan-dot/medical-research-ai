<script setup lang="ts">
defineProps<{ exporting: boolean }>();
const emit = defineEmits<{ export: [format: "csv" | "ris" | "bibtex"] }>();
</script>

<template>
  <details class="export-menu">
    <summary>导出</summary>
    <div class="export-popover">
      <strong>导出当前筛选结果</strong>
      <p>导出文献数据，不包含 PDF 全文</p>
      <button v-for="format in ['csv', 'ris', 'bibtex'] as const" :key="format" type="button" :data-format="format" :disabled="exporting" @click="emit('export', format)">
        {{ format === 'bibtex' ? 'BibTeX' : format.toUpperCase() }}
      </button>
    </div>
  </details>
</template>

<style scoped>
.export-menu{position:relative}.export-menu summary{list-style:none;cursor:pointer;border:1px solid #d7dce4;border-radius:4px;padding:6px 12px;background:#fff;font-size:13px}.export-menu summary::-webkit-details-marker{display:none}.export-popover{position:absolute;z-index:8;right:0;top:38px;width:230px;padding:14px;border:1px solid #d7dce4;border-radius:6px;background:#fff;box-shadow:0 10px 30px #17233b22}.export-popover strong{font-size:13px}.export-popover p{margin:5px 0 10px;color:#7a8494;font-size:11px}.export-popover button{width:100%;padding:7px 8px;border:0;background:transparent;text-align:left;cursor:pointer}.export-popover button:hover{background:#f3f5f8}.export-popover button:disabled{opacity:.5}
</style>
