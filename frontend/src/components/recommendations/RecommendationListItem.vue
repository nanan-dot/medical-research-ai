<script setup lang="ts">
import AbstractDisclosure from "../literature/AbstractDisclosure.vue";
import FulltextAccess from "../literature/FulltextAccess.vue";
import PubMedLink from "../literature/PubMedLink.vue";
import type { RecommendationItem } from "../../api/recommendations";

defineProps<{ item: RecommendationItem; priority: number }>();
</script>

<template>
  <li class="recommendation-row">
    <span class="priority" :aria-label="`优先阅读第 ${priority} 篇`">{{ String(priority).padStart(2, "0") }}</span>
    <article class="citation">
      <p class="metadata"><span>PMID {{ item.citation.pmid }}</span><span v-if="item.citation.year">{{ item.citation.year }}</span><span v-if="item.citation.journal">{{ item.citation.journal }}</span></p>
      <h3>{{ item.citation.title || "题名未提供" }}</h3>
      <p class="authors">{{ item.citation.authors.join(", ") || "作者信息未提供" }}</p>
      <AbstractDisclosure :abstract-text="item.citation.abstract" />
      <div class="links"><PubMedLink :pmid="item.citation.pmid" /><FulltextAccess :item="null" /></div>
      <p class="provenance">服务端元数据 · {{ item.citation.verified_on || "核验日期未提供" }}</p>
    </article>
    <aside class="reason" aria-label="推荐理由"><span>推荐理由</span><p>{{ item.recommendation_reason }}</p><small>原样显示服务端返回内容</small></aside>
  </li>
</template>

<style scoped>
.recommendation-row{display:grid;grid-template-columns:28px minmax(0,1fr) 240px;gap:12px;padding:12px 16px;border-bottom:1px solid var(--border-subtle)}.recommendation-row:last-child{border:0}.priority{display:grid;place-items:center;align-self:start;min-height:24px;background:var(--color-primary);border-radius:4px;color:#fff;font:700 .75rem ui-monospace,SFMono-Regular,Consolas,monospace;font-variant-numeric:tabular-nums}.citation{display:grid;gap:6px;min-width:0}.metadata,.authors,.provenance{margin:0;color:var(--text-muted);font-size:.78rem;overflow-wrap:anywhere}.metadata{display:flex;flex-wrap:wrap;gap:8px;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-variant-numeric:tabular-nums}.citation h3{margin:0;font-size:.96rem;line-height:1.45;overflow-wrap:anywhere}.links{display:flex;flex-wrap:wrap;gap:12px;align-items:center}.provenance{font-size:.7rem}.reason{padding:8px 12px;border-left:2px solid var(--color-primary);background:var(--color-primary-soft)}.reason>span{color:var(--color-primary);font-size:.72rem;font-weight:700}.reason p{margin:6px 0;line-height:1.55;font-size:.82rem;overflow-wrap:anywhere}.reason small{color:var(--text-muted);font-size:.7rem}@media(max-width:900px){.recommendation-row{grid-template-columns:28px minmax(0,1fr)}.reason{grid-column:2;border-left-width:2px}}@media(prefers-reduced-motion:no-preference){.recommendation-row{transition:background-color 80ms ease}.recommendation-row:hover{background:var(--surface-muted)}}
</style>
