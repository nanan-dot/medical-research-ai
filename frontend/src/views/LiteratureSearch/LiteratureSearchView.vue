<script setup lang="ts">
// 文献检索工作空间：从临床问题建立可追溯检索策略。
// 真实管线：parse-query（解析研究问题→候选条件）→ expand-terms（关键词扩展）
// → build-query（构建检索式）→ createTask（执行检索）。所有数据来自真实后端，
// 不伪造检索完成/论文数量/进度。空态与禁用态诚实表达能力边界。
import { computed, reactive, shallowRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useQueryIntent } from "../../composables/useQueryIntent";
import { useSearchTerms } from "../../composables/useSearchTerms";
import LiteratureWorkspaceTabs from "./LiteratureWorkspaceTabs.vue";
import SearchStrategyBuilder from "./SearchStrategyBuilder.vue";
import SearchDraftPanel from "./SearchDraftPanel.vue";
import SourceScopePanel from "./SourceScopePanel.vue";
import SearchReadinessPanel from "./SearchReadinessPanel.vue";

const route = useRoute();
const router = useRouter();

const { parsed, candidate, loading: intentLoading, error: intentError, parse, updateCandidate } = useQueryIntent();
const { expanded, result, loading: termsLoading, error: termsError, taskLoading, taskError, expand, build, createTask } = useSearchTerms();

const topic = shallowRef("");
// PICO 受控状态：reactive 保证子组件 emit 后响应式更新。
const pico = reactive({ population: "", intervention: "", comparison: "", outcome: "" });
const selectedSources = shallowRef<string[]>(["pubmed"]);

const loading = computed(() => intentLoading.value || termsLoading.value);
const error = computed(() => intentError.value || termsError.value);

// 顶部栏/工作台跳转时携带的 raw_topic 预填（仅当路由可用时）。
const routeQuery = route?.query;
if (routeQuery && typeof routeQuery.raw_topic === "string" && routeQuery.raw_topic) {
  topic.value = routeQuery.raw_topic;
}

async function handleSubmit(rawTopic: string): Promise<void> {
  topic.value = rawTopic;
  await parse(rawTopic);
  // parse 完成后重新读取候选（composable 的 candidate 是 computed，依赖 parsed 更新）。
  const cand = parsed.value?.candidate;
  // parse-query 成功后：真实候选回填 PICO 四个条件（仅当解析成功且有数据时）。
  // candidate 字段是后端真实产物；无对应数据时保持空，不生成虚构内容。
  if (!cand) return;
  pico.population = cand.disease ?? "";
  pico.intervention = cand.intervention ?? "";
  pico.comparison = "";
  pico.outcome = "";
  // 解析成功后立即扩展关键词（真实 expand-terms 调用）。
  // candidate 为只读类型，展开为可变对象传给 expand（composable 需要可变 SearchIntentCandidate）。
  await expand({
    ...cand,
    study_types: [...(cand.study_types ?? [])],
    language: [...(cand.language ?? [])],
    exclusions: [...(cand.exclusions ?? [])],
    date_range: cand.date_range ? { ...cand.date_range } : null,
  });
  // 仅当扩展出可检索的英文词条时才构建检索式；中文词被后端省略时
  // （warnings 提示"保留编辑但省略出查询"）保持空态，不把空组发往后端。
  const groups = expanded.value?.term_groups ?? [];
  if (groups.some((group) => group.terms.length > 0)) {
    await build(groups);
  }
}

function handlePicoChange(next: { population: string; intervention: string; comparison: string; outcome: string }): void {
  pico.population = next.population;
  pico.intervention = next.intervention;
  pico.comparison = next.comparison;
  pico.outcome = next.outcome;
}

function handleSourceChange(selected: string[]): void {
  selectedSources.value = selected;
}

function handleBuild(groups: unknown[]): void {
  void build(groups as Parameters<typeof build>[0]);
}

function saveDraft(): void {
  // 本地草稿边界：仅保存在浏览器 localStorage，不伪称已保存到后端。
  if (result.value) {
    window.localStorage.setItem("rag-medicine-search-draft", result.value.boolean_query);
  }
}

function copyQuery(): void {
  if (result.value) void window.navigator.clipboard?.writeText(result.value.boolean_query);
}

// 执行检索：真实 createTask（调用后端 PubMed 检索），成功后跳转结果页。
// 与工作台研究起点的四步流程一致：解析→扩展→构建→创建。
async function runSearch(): Promise<void> {
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

const topicFilled = computed(() => topic.value.trim().length > 0);
const picoFilled = computed(() =>
  [pico.population, pico.intervention, pico.comparison, pico.outcome].some((v) => v.trim().length > 0),
);
const sourceSelected = computed(() => selectedSources.value.length > 0);
const draftReady = computed(() => Boolean(result.value?.boolean_query));
</script>

<template>
  <main class="literature-workspace">
    <header class="page-header">
      <h1 class="page-title">文献检索</h1>
      <p class="page-copy">从临床问题出发，建立可复用、可追溯的检索策略。</p>
    </header>

    <LiteratureWorkspaceTabs />

    <SearchStrategyBuilder
      :loading="loading"
      :error="error"
      :has-candidate="Boolean(candidate)"
      :pico="pico"
      @submit="handleSubmit"
      @pico-change="handlePicoChange"
    />

    <div class="workspace-columns">
      <SearchDraftPanel
        :expanded="expanded"
        :result="result"
        :loading="termsLoading"
        @build="handleBuild"
        @copy="copyQuery"
      />
      <SourceScopePanel @change="handleSourceChange" />
    </div>

    <SearchReadinessPanel
      :topic-filled="topicFilled"
      :pico-filled="picoFilled"
      :source-selected="sourceSelected"
      :draft-ready="draftReady"
      :task-loading="taskLoading"
      :task-error="taskError"
      :has-candidate="Boolean(candidate)"
      @save-draft="saveDraft"
      @run-search="runSearch"
    />
  </main>
</template>

<style scoped>
.literature-workspace {
  max-width: 1180px;
  margin: 0 auto;
  padding: 1.4rem 1.2rem 2.6rem;
  display: grid;
  gap: 1rem;
}
.page-header {
  display: grid;
  gap: 0.2rem;
}
.page-title {
  margin: 0;
  color: var(--text-primary, #0f2a43);
  font-size: 1.6rem;
  line-height: 1.2;
}
.page-copy {
  margin: 0;
  color: var(--text-muted, #64748b);
  font-size: 0.9rem;
}
.workspace-columns {
  display: grid;
  grid-template-columns: 8fr 4fr;
  gap: 1rem;
  align-items: start;
}
@media (max-width: 900px) {
  .workspace-columns {
    grid-template-columns: 1fr;
  }
}
</style>
