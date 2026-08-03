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

function saveDraft() {
  if (result.value) window.localStorage.setItem("rag-medicine-search-draft", result.value.boolean_query);
}

async function copyQuery() {
  if (result.value) await window.navigator.clipboard?.writeText(result.value.boolean_query);
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
    <section v-if="result" class="pubmed-boundary" aria-label="PubMed result availability">
      <p class="eyebrow">PUBMED RESULTS · MOCK</p>
      <h2>真实 PubMed 检索将在 R2-WP03 接入</h2>
      <p>当前页面只构建可复制、可编辑的检索式；不会显示或伪造任何 PubMed 文献、PMID、DOI、引文次数或期刊指标。</p>
      <div class="draft-actions"><button type="button" @click="saveDraft">保存本地草稿</button><button type="button" @click="copyQuery">复制检索式</button></div>
    </section>
  </main>
</template>

<style scoped>
.literature-search { max-width:1100px; margin:auto; padding:2rem 1.2rem 3rem; display:grid; gap:1rem; }.eyebrow { margin:0; color:var(--color-primary); font-weight:800; letter-spacing:.12em; font-size:.72rem; }.page-title { margin:.25rem 0; color:var(--text-primary); font-size:clamp(2rem,4vw,3.2rem); line-height:1.1; }.page-copy { max-width:720px; color:var(--text-muted); }.topic-form { display:flex; gap:.75rem; padding:1rem; background:var(--paper); border:1px solid var(--border-subtle); border-radius:var(--radius-lg); }.topic-label { flex:1; display:grid; gap:.35rem; font-weight:700; color:var(--text-primary); }.topic-label input { padding:.75rem; border:1px solid var(--border-strong); border-radius:8px; font:inherit; }.topic-form button,.expand-button,.draft-actions button { align-self:end; padding:.7rem 1rem; border:0; border-radius:8px; background:var(--color-primary); color:#fff; font-weight:700; }.expand-button { justify-self:start; }.request-error { margin:0; padding:.8rem; color:var(--color-danger); background:var(--color-danger-soft); border-radius:10px; }.result-meta { padding:1rem; border-left:4px solid var(--color-primary); background:var(--color-primary-soft); }.pubmed-boundary { display:grid; gap:.45rem; padding:1rem; border:1px dashed var(--border-strong); border-radius:var(--radius-md); background:var(--surface-muted); }.pubmed-boundary h2,.pubmed-boundary p { margin:0; }.pubmed-boundary p:not(.eyebrow){color:var(--text-muted)}.draft-actions{display:flex;gap:.6rem}@media (max-width:640px){.topic-form{display:grid;}}
</style>
