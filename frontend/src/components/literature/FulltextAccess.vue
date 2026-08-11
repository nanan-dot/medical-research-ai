<script setup lang="ts">
import { computed } from "vue";

import type { LibraryItem } from "../../api/literatureSearch";

const props = defineProps<{ item: LibraryItem | null }>();
const localDocumentId = computed(() =>
  props.item?.fulltext_status === "local_pdf_available" ? props.item.document_id : null,
);
const openAccessUrl = computed(() =>
  props.item?.fulltext_status === "open_access_available" && props.item.pmcid
    ? `https://pmc.ncbi.nlm.nih.gov/articles/${props.item.pmcid}/`
    : null,
);
</script>

<template>
  <span class="fulltext-access">
    <RouterLink v-if="localDocumentId" :to="`/documents/${localDocumentId}`">查看本地全文</RouterLink>
    <a v-else-if="openAccessUrl" :href="openAccessUrl" target="_blank" rel="noopener noreferrer">查看开放全文</a>
    <span v-else>全文获取受限</span>
  </span>
</template>

<style scoped>
.fulltext-access { color: var(--text-muted); font-size: .82rem; }
a { color: var(--color-primary); font-weight: 700; }
</style>
