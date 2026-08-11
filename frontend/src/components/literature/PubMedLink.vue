<script setup lang="ts">
defineProps<{ pmid: string }>();
</script>

<template>
  <a :href="`https://pubmed.ncbi.nlm.nih.gov/${pmid}/`" target="_blank" rel="noopener noreferrer">查看 PubMed ↗</a>
</template>

<style scoped>
a { color: var(--color-primary); font-size: .82rem; font-weight: 700; }
</style>
