<script setup lang="ts">
import { shallowRef } from "vue";
import SearchTermsEditor from "../../components/SearchTermsEditor/SearchTermsEditor.vue";
import { useQueryIntent } from "../../composables/useQueryIntent";
import { useSearchTerms } from "../../composables/useSearchTerms";
import QueryBuilder from "./QueryBuilder.vue";

const rawTopic = shallowRef("");
const { parsed, candidate, loading: intentLoading, error: intentError, parse, updateCandidate } = useQueryIntent();
const { expanded, result, loading: termsLoading, error: termsError, expand, build } = useSearchTerms();

async function submit() {
  if (!rawTopic.value.trim()) return;
  await parse(rawTopic.value);
}
</script>

<template>
  <main class="literature-search">
    <header class="page-header">
      <p class="eyebrow">LITERATURE SEARCH</p>
      <h1 class="page-title">确认检索需求，再构建检索词</h1>
      <p class="page-copy">系统先给出候选条件，再提供可编辑的英文关键词、同义词和来源标注的 MeSH 候选。</p>
    </header>
    <form class="topic-form" @submit.prevent="submit">
      <label class="topic-label">研究主题<input v-model="rawTopic" maxlength="1000" required /></label>
      <button :disabled="intentLoading">{{ intentLoading ? "解析中…" : "生成候选条件" }}</button>
    </form>
    <p v-if="intentError" class="request-error" role="alert">{{ intentError }}</p>
    <section v-if="parsed" class="result-meta"><p>原始主题：{{ parsed.raw_topic }}</p><p>候选来源：{{ parsed.candidate_source === "rule_fallback" ? "规则候选" : "模型候选" }}</p></section>
    <QueryBuilder v-if="candidate" :candidate="candidate" @update-candidate="updateCandidate" />
    <button v-if="candidate" class="expand-button" :disabled="termsLoading" @click="expand(candidate)">{{ termsLoading ? "处理中…" : "扩展关键词与 MeSH" }}</button>
    <p v-if="termsError" class="request-error" role="alert">{{ termsError }}</p>
    <SearchTermsEditor v-if="expanded" :expanded="expanded" :result="result" :loading="termsLoading" @build="build" />
  </main>
</template>

<style scoped>
.literature-search { max-width: 960px; margin: auto; padding: 4rem 1rem; display: grid; gap: 1.25rem; }.eyebrow { margin: 0; color: #a94d2d; font-weight: 800; letter-spacing: .14em; }.page-title { margin: .25rem 0; color: #173f3c; font: 700 clamp(2.2rem, 6vw, 4rem)/1.05 Georgia, serif; }.page-copy { max-width: 680px; color: #53686b; }.topic-form { display: flex; gap: .75rem; padding: 1rem; background: #fff; border-radius: 16px; }.topic-label { flex: 1; display: grid; gap: .35rem; font-weight: 700; color: #40585a; }.topic-label input { padding: .65rem; border: 1px solid #aabbbb; border-radius: 8px; font: inherit; }.topic-form button, .expand-button { align-self: end; padding: .7rem 1rem; border: 0; border-radius: 8px; background: #173f3c; color: #fff; font-weight: 700; }.expand-button { justify-self: start; }.request-error { margin: 0; padding: .8rem; color: #8b2c19; background: #fee5de; border-radius: 10px; }.result-meta { padding: 1rem; border-left: 4px solid #d8a347; background: #fff8e9; } @media (max-width: 640px) { .topic-form { display: grid; } }
</style>
