<script setup lang="ts">
import { onMounted } from "vue";

import DocumentFilters from "./DocumentFilters.vue";
import DocumentTable from "./DocumentTable.vue";
import { useDocuments } from "../../composables/useDocuments";

const {
  documents, filters, total, loading, error, pageNumber, hasPrevious, hasNext,
  load, applyFilters, retryParse, retryIndex, deleteIndex, previousPage, nextPage,
} = useDocuments();

onMounted(load);
</script>

<template>
  <section class="manager" aria-labelledby="documents-title">
    <header class="manager-header">
      <div><p class="eyebrow">DOCUMENT PIPELINE</p><h2 id="documents-title">文档任务状态</h2></div>
      <p class="summary">{{ total }} 篇文档</p>
    </header>
    <DocumentFilters :filters="filters" :disabled="loading" @change="applyFilters" />
    <p v-if="error" class="request-error" role="alert">{{ error }}</p>
    <DocumentTable
      :documents="documents"
      :disabled="loading"
      @retry-parse="retryParse"
      @retry-index="retryIndex"
      @delete-index="deleteIndex"
    />
    <footer class="pagination">
      <button :disabled="loading || !hasPrevious" @click="previousPage">上一页</button>
      <span>第 {{ pageNumber }} 页</span>
      <button :disabled="loading || !hasNext" @click="nextPage">下一页</button>
    </footer>
  </section>
</template>

<style scoped>
.manager { display: grid; gap: 1.3rem; padding: 1.5rem; border: 1px solid rgba(22, 83, 78, 0.14); border-radius: 20px; background: rgba(250, 252, 249, 0.96); box-shadow: 0 24px 70px rgba(31, 64, 61, 0.12); }
.manager-header { display: flex; align-items: end; justify-content: space-between; gap: 1rem; }
.manager-header h2 { margin: 0.1rem 0 0; font-size: clamp(1.5rem, 4vw, 2.3rem); }
.eyebrow { margin: 0; color: #0d6f66; font-size: 0.72rem; font-weight: 900; letter-spacing: 0.14em; }
.summary { color: #607276; }
.request-error { margin: 0; padding: 0.8rem; border-radius: 10px; background: #fee5de; color: #8b2c19; }
.pagination { display: flex; align-items: center; justify-content: center; gap: 1rem; }
.pagination button { border: 1px solid #bdcbcc; border-radius: 8px; padding: 0.5rem 0.8rem; background: #fff; }
</style>
