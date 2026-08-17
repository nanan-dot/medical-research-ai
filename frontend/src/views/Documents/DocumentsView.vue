Exit code: 0
Wall time: 2 seconds
Output:
<script setup lang="ts">
import DocumentManager from "../../components/document/DocumentManager.vue";
</script>

<template>
  <main class="documents-page">
    <DocumentManager />
  </main>
</template>

<style scoped>
.documents-page {
  width: min(100% - 3rem, 1400px);
  margin: 0 auto;
  padding: 4px 0 48px;
}

@media (max-width: 700px) {
  .documents-page {
    width: min(100% - 2rem, 1400px);
  }
}
</style>
