<script setup lang="ts">
import KnowledgeSourceManager from "../../components/knowledge-source/KnowledgeSourceManager.vue";
</script>

<template>
  <main
    class="knowledge-page"
    data-testid="knowledge-base-page"
  >
    <KnowledgeSourceManager />
  </main>
</template>

<style scoped>
.knowledge-page {
  width: min(100% - 2.5rem, 1230px);
  margin: 0 auto;
  padding: 12px 0 28px;
}

@media (max-width: 767px) {
  .knowledge-page {
    width: min(100% - 1.5rem, 1230px);
    padding-top: 10px;
  }
}
</style>
