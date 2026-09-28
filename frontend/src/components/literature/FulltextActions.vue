<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";

import type { CitationItem, LibraryItem } from "../../api/literatureSearch";
import { useFulltextAccess } from "../../composables/useFulltextAccess";

const props = defineProps<{ resultId: number; citation: CitationItem; libraryItem: LibraryItem | null }>();
const emit = defineEmits<{ updated: [item: LibraryItem] }>();
const access = useFulltextAccess({ resultId: props.resultId, citation: props.citation, initialItem: props.libraryItem, onUpdated: (item) => emit("updated", item) });
const pubmedUrl = computed(() => /^\d+$/.test(props.citation.pmid) ? `https://pubmed.ncbi.nlm.nih.gov/${props.citation.pmid}/` : null);
const doiUrl = computed(() => {
  const doi = props.citation.doi?.trim();
  return doi && /^10\.\d{4,9}\/[\w.()/:;-]+$/i.test(doi) ? `https://doi.org/${doi}` : null;
});

</script>

<template>
  <div class="fulltext-actions" :aria-busy="access.isBusy.value">
    <RouterLink v-if="access.hasLocalFulltext.value" class="primary-action" :to="`/documents/${access.item.value?.document_id}`">打开本地全文</RouterLink>
    <button v-else-if="props.citation.pmcid && !access.error.value" type="button" class="primary-action" data-action="pmc" :disabled="access.isBusy.value" @click="access.acquirePmc">
      {{ access.phase.value === "saving" ? "正在保存元数据…" : access.phase.value === "acquiring" ? "正在核验与下载…" : "获取 PMC 开放全文" }}
    </button>
    <a v-else-if="pubmedUrl" class="primary-action" :href="pubmedUrl" target="_blank" rel="noopener noreferrer">访问 PubMed ↗</a>

    <a v-if="props.citation.pmcid && pubmedUrl" :href="pubmedUrl" target="_blank" rel="noopener noreferrer">访问 PubMed ↗</a>
    <a v-if="doiUrl" :href="doiUrl" target="_blank" rel="noopener noreferrer">登录后获取全文 ↗</a>
    <span class="external-note">外部页面 · 用户自行获取全文；系统不保存账号信息</span>

    <p class="status" role="status" aria-live="polite" aria-atomic="true">
      <template v-if="access.hasLocalFulltext.value">全文已获取，可前往资料库查看。</template>
    </p>
    <p v-if="access.error.value" role="alert">{{ access.error.value }}</p>
  </div>
</template>

<style scoped>
.fulltext-actions { display: flex; flex-wrap: wrap; align-items: center; gap: .4rem; }
.fulltext-actions button, .fulltext-actions a { min-height: 2rem; padding: .32rem .55rem; border: 1px solid var(--border-strong); border-radius: 6px; background: var(--surface); color: var(--color-primary); font: inherit; cursor: pointer; }
.fulltext-actions button:focus-visible, .fulltext-actions a:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
.primary-action { font-weight: 750; }
.external-note, .status { width: 100%; margin: 0; color: var(--text-muted); font-size: .72rem; }
[role="alert"] { width: 100%; margin: 0; color: var(--color-danger); }
</style>
