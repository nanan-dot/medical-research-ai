<script setup lang="ts">
import DocumentManager from "../../components/document/DocumentManager.vue";
</script>

<template>
  <main class="documents-page">
    <DocumentManager />
  </main>
</template>

<style scoped>
.documents-page { width: min(100% - 3rem, 1440px); margin: 0 auto; padding: 1rem 0 2.75rem; display:grid; gap:1rem; }
</style>
