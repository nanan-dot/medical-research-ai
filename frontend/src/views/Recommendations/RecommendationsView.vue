<script setup lang="ts">
import { computed, shallowRef } from "vue";

import RecommendationListItem from "../../components/recommendations/RecommendationListItem.vue";
import RecommendationQueryPanel from "../../components/recommendations/RecommendationQueryPanel.vue";
import RecommendationSkeleton from "../../components/recommendations/RecommendationSkeleton.vue";
import { useRecommendations } from "../../composables/useRecommendations";

const props = withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false });
const query = shallowRef("");
const candidateCount = shallowRef(5);
const { result, loading, error, recommend } = useRecommendations();
const statusLabel = computed(() => {
  if (result.value?.status === "unavailable") return "服务暂不可用";
  if (result.value?.status === "completed_with_warnings") return "完成，含服务端提示";
  return "已完成";
});

async function submit(): Promise<void> {
  const topic = query.value.trim();
  if (topic) await recommend(topic, candidateCount.value);
}
</script>

<template>
  <main class="recommendation-page">
    <header v-if="!props.embedded" class="page-header">
      <div><p class="eyebrow">文献检索 / 推荐阅读</p><h1>推荐阅读</h1><p>从研究问题生成可核验的优先阅读清单。</p></div>
      <span class="boundary-note">仅 PubMed 数据源</span>
    </header>

    <RecommendationQueryPanel v-model:query="query" v-model:candidate-count="candidateCount" :loading="loading" @submit="submit" />

    <p v-if="error" class="state error" role="alert">{{ error }}。请检查服务后重试。</p>
    <RecommendationSkeleton v-else-if="loading" />
    <section v-else-if="result" class="results" aria-live="polite">
      <header class="results-header">
        <div><p class="eyebrow">服务端推荐结果</p><h2>{{ result.items.length }} 篇文献</h2></div>
        <span class="status" :class="result.status">{{ statusLabel }}</span>
      </header>
      <div v-if="result.warnings.length" class="warnings" role="status"><strong>服务端提示</strong><span v-for="warning in result.warnings" :key="warning">{{ warning }}</span></div>
      <div v-if="result.status === 'unavailable'" class="empty-state"><h3>推荐服务暂不可用</h3><p>服务端未返回可展示的推荐文献；请稍后重试。</p></div>
      <div v-else-if="!result.items.length" class="empty-state"><h3>没有找到可核验文献</h3><p>可补充研究对象、干预或结局术语后重新检索。系统不会补造论文。</p></div>
      <ol v-else class="result-list"><RecommendationListItem v-for="(item, index) in result.items" :key="item.citation.pmid" :item="item" :priority="index + 1" /></ol>
    </section>
    <section v-else class="empty-state initial"><h2>从一个研究问题开始</h2><p>仅在服务端返回 PubMed 推荐后展示文献与推荐理由。</p></section>
  </main>
</template>

<style scoped>
.recommendation-page{display:grid;gap:16px;width:100%;box-sizing:border-box;max-width:1440px;margin:0 auto;padding:16px 24px 32px;color:var(--text-primary)}.page-header,.results-header{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}.page-header{padding-bottom:12px;border-bottom:1px solid var(--border-subtle)}.eyebrow{margin:0;color:var(--color-primary);font-size:.72rem;font-weight:700;letter-spacing:.04em}.page-header h1{margin:4px 0;font-size:1.5rem;line-height:1.25}.page-header p:not(.eyebrow){margin:0;color:var(--text-muted);font-size:.86rem}.boundary-note,.status{padding:4px 8px;border:1px solid var(--border-subtle);border-radius:4px;background:var(--surface-muted);color:var(--text-secondary);font-size:.72rem;font-weight:700}.results{overflow:hidden;border:1px solid var(--border-subtle);border-radius:8px;background:var(--surface)}.results-header{align-items:end;padding:12px 16px;border-bottom:1px solid var(--border-subtle)}.results-header h2{margin:3px 0 0;font-size:1rem}.status.completed{color:var(--color-success)}.status.completed_with_warnings{color:#92400e;background:var(--color-warning-soft)}.status.unavailable{color:var(--color-danger)}.warnings{display:flex;gap:8px;flex-wrap:wrap;padding:8px 16px;border-bottom:1px solid var(--border-subtle);background:var(--color-warning-soft);color:#92400e;font-size:.78rem}.result-list{margin:0;padding:0;list-style:none}.state,.empty-state{margin:0;padding:24px 16px;border:1px dashed var(--border-strong);border-radius:8px;color:var(--text-muted);text-align:center}.state.error{border-style:solid;border-color:var(--color-danger);background:var(--color-danger-soft);color:var(--color-danger);text-align:left}.empty-state h2,.empty-state h3{margin:0 0 8px;color:var(--text-primary);font-size:1rem}.empty-state p{max-width:560px;margin:0 auto;line-height:1.6;font-size:.84rem}.initial{padding:48px 16px}@media(max-width:640px){.recommendation-page{padding:12px 16px 24px}.page-header,.results-header{align-items:stretch;flex-direction:column}.boundary-note,.status{align-self:flex-start}}
</style>
