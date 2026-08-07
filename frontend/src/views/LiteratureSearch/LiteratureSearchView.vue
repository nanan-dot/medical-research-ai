<script setup lang="ts">
import { shallowRef } from "vue";
import { useRouter } from "vue-router";
import SearchTermsEditor from "../../components/SearchTermsEditor/SearchTermsEditor.vue";
import { useQueryIntent } from "../../composables/useQueryIntent";
import { useSearchTerms } from "../../composables/useSearchTerms";
import QueryBuilder from "./QueryBuilder.vue";

const router = useRouter();
const rawTopic = shallowRef("");
const { parsed, candidate, loading: intentLoading, error: intentError, parse, updateCandidate } = useQueryIntent();
const { expanded, result, loading: termsLoading, error: termsError, taskLoading, taskError, expand, build, createTask } = useSearchTerms();

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

// 执行检索：把已构建的检索式提交为检索任务（立即真实检索 PubMed），
// 成功后跳转到结果页。original_query 用用户在第一步输入的原始主题，
// 保证检索历史可回溯；structured_query/filters 为输入快照，供重跑复现。
async function runSearch() {
  if (!result.value || !parsed.value) return;
  const task = await createTask({
    original_query: parsed.value.raw_topic,
    structured_query: JSON.stringify(parsed.value.candidate),
    search_string: result.value.boolean_query,
    filters: JSON.stringify({}),
    model_version: parsed.value.prompt_version,
    user_edits: JSON.stringify(result.value.user_edits),
    retmax: parsed.value.candidate.retmax || 20,
  });
  if (task !== null && task.latest_result_id !== null) {
    await router.push(`/literature-search/results/${task.latest_result_id}`);
  }
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
    <section v-if="result" class="execute-boundary" aria-label="PubMed result availability">
      <p class="eyebrow">PUBMED EXECUTE</p>
      <h2>执行 PubMed 检索</h2>
      <p>确认上面的检索式后，创建检索任务会立即调用 PubMed 检索并将结果保存到历史。</p>
      <div class="draft-actions">
        <button type="button" @click="saveDraft">保存本地草稿</button>
        <button type="button" @click="copyQuery">复制检索式</button>
        <button type="button" class="execute-button" :disabled="taskLoading" @click="runSearch">{{ taskLoading ? "检索中…" : "执行检索" }}</button>
      </div>
      <p v-if="taskError" class="request-error" role="alert">{{ taskError }}</p>
    </section>
  </main>
</template>

<style scoped>
.literature-search { max-width:1100px; margin:auto; padding:2rem 1.2rem 3rem; display:grid; gap:1rem; }.eyebrow { margin:0; color:var(--color-primary); font-weight:800; letter-spacing:.12em; font-size:.72rem; }.page-title { margin:.25rem 0; color:var(--text-primary); font-size:clamp(2rem,4vw,3.2rem); line-height:1.1; }.page-copy { max-width:720px; color:var(--text-muted); }.topic-form { display:flex; gap:.75rem; padding:1rem; background:var(--paper); border:1px solid var(--border-subtle); border-radius:var(--radius-lg); }.topic-label { flex:1; display:grid; gap:.35rem; font-weight:700; color:var(--text-primary); }.topic-label input { padding:.75rem; border:1px solid var(--border-strong); border-radius:8px; font:inherit; }.topic-form button,.expand-button,.draft-actions button { align-self:end; padding:.7rem 1rem; border:0; border-radius:8px; background:var(--color-primary); color:#fff; font-weight:700; }.expand-button { justify-self:start; }.request-error { margin:0; padding:.8rem; color:var(--color-danger); background:var(--color-danger-soft); border-radius:10px; }.result-meta { padding:1rem; border-left:4px solid var(--color-primary); background:var(--color-primary-soft); }.execute-boundary { display:grid; gap:.45rem; padding:1rem; border:1px dashed var(--border-strong); border-radius:var(--radius-md); background:var(--surface-muted); }.execute-boundary h2,.execute-boundary p { margin:0; }.execute-boundary p:not(.eyebrow){color:var(--text-muted)}.draft-actions{display:flex;gap:.6rem}.execute-button:disabled{opacity:.6;cursor:wait}@media (max-width:640px){.topic-form{display:grid;}}
</style>
