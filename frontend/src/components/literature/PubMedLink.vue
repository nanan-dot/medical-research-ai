<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ pmid: string }>();
const pubmedUrl = computed(() => /^\d+$/.test(props.pmid) ? `https://pubmed.ncbi.nlm.nih.gov/${props.pmid}/` : null);
</script>

<template>
  <a v-if="pubmedUrl" :href="pubmedUrl" target="_blank" rel="noopener noreferrer">查看 PubMed ↗</a>
  <span v-else>PubMed 标识无效</span>
</template>

<style scoped>
a { color: var(--color-primary); font-size: .82rem; font-weight: 700; }
</style>
