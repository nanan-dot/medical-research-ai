Exit code: 0
Wall time: 2 seconds
Output:
<script setup lang="ts">
import DocumentManager from "../../components/document/DocumentManager.vue";
</script>

<template>
  <main class="documents-page">
    <header class="documents-heading">
      <h1>文档库</h1>
      <p>查看知识来源同步产生的科研文档，支持文档检索、状态确认与问题修复。</p>
    </header>
    <DocumentManager />
  </main>
</template>

<style scoped>
.documents-page {
  width: min(100% - 3rem, 1400px);
  margin: 0 auto;
  padding: 22px 0 48px;
}

.documents-heading {
  margin: 0 0 14px;
}

.documents-heading h1 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.45rem;
  letter-spacing: -.02em;
}

.documents-heading p {
  margin: 5px 0 0;
  color: var(--text-muted);
  font-size: .78rem;
}

@media (max-width: 700px) {
  .documents-page {
    width: min(100% - 2rem, 1400px);
    padding-top: 16px;
  }
}
</style>
