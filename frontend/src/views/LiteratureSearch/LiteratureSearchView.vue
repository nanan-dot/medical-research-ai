<script setup lang="ts">
// 文献检索工作空间：从临床问题建立可追溯检索策略。
// 真实管线：parse-query（解析研究问题→候选条件）→ expand-terms（关键词扩展）
// → build-query（构建检索式）→ createTask（执行检索）。所有数据来自真实后端，
// 不伪造检索完成/论文数量/进度。空态与禁用态诚实表达能力边界。
import { computed, reactive, shallowRef } from "vue";
import { useRoute } from "vue-router";
import { useQueryIntent } from "../../composables/useQueryIntent";
import { useSearchTerms } from "../../composables/useSearchTerms";
import LiteratureWorkspaceTabs from "./LiteratureWorkspaceTabs.vue";
import SearchStrategyBuilder from "./SearchStrategyBuilder.vue";
import SearchDraftPanel from "./SearchDraftPanel.vue";
import SourceScopePanel from "./SourceScopePanel.vue";
import SearchReadinessPanel from "./SearchReadinessPanel.vue";
import ResultsView from "./ResultsView.vue";
import History from "./History.vue";
import RecommendationsView from "../Recommendations/RecommendationsView.vue";

const route = useRoute();

const { parsed, candidate, loading: intentLoading, error: intentError, parse, updateCandidate } = useQueryIntent();
const { expanded, result, loading: termsLoading, error: termsError, taskLoading, taskError, expand, build, createTask } = useSearchTerms();

const topic = shallowRef("");
const editableQuery = shallowRef("");
// PICO 受控状态：reactive 保证子组件 emit 后响应式更新。
const pico = reactive({ population: "", intervention: "", comparison: "", outcome: "" });
const selectedSources = shallowRef<string[]>(["pubmed"]);
const publicationLanguage = shallowRef<"any" | "chinese">("any");
const activeTab = shallowRef<"center" | "results" | "history" | "recommendations">("center");
const activeResult = shallowRef<{ resultId: number; taskId: number } | null>(null);

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
  pico.comparison = cand.comparison ?? "";
  pico.outcome = cand.outcome ?? "";
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
    editableQuery.value = result.value?.boolean_query ?? "";
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

function handleLanguageChange(value: "any" | "chinese"): void {
  publicationLanguage.value = value;
}

function clearStrategyInput(): void {
  pico.population = "";
  pico.intervention = "";
  pico.comparison = "";
  pico.outcome = "";
  topic.value = "";
}

function saveDraft(): void {
  // 本地草稿边界：仅保存在浏览器 localStorage，不伪称已保存到后端。
  if (editableQuery.value.trim()) {
    window.localStorage.setItem("rag-medicine-search-draft", editableQuery.value);
  }
}

function copyQuery(): void {
  if (editableQuery.value) void window.navigator.clipboard?.writeText(editableQuery.value);
}

// 执行检索：真实 createTask（调用后端 PubMed 检索），成功后在本页面切换至结果展示。
async function runSearch(): Promise<void> {
  if (!result.value || !parsed.value || !editableQuery.value.trim()) return;
  const task = await createTask({
    original_query: parsed.value.raw_topic,
    structured_query: JSON.stringify(parsed.value.candidate),
    search_string: publicationLanguage.value === "chinese"
      ? `(${editableQuery.value}) AND chinese[la]`
      : editableQuery.value,
    filters: JSON.stringify({ publication_language: publicationLanguage.value }),
    model_version: parsed.value.prompt_version,
    user_edits: JSON.stringify(result.value.user_edits),
    retmax: parsed.value.candidate.retmax || 20,
  });
  if (task !== null && task.latest_result_id !== null) {
    activeResult.value = { resultId: task.latest_result_id, taskId: task.id };
    activeTab.value = "results";
  }
}

const topicFilled = computed(() => topic.value.trim().length > 0);
const sourceSelected = computed(() => selectedSources.value.length > 0);
const draftReady = computed(() => Boolean(result.value?.boolean_query && editableQuery.value.trim()));
</script>

<template>
  <main class="literature-workspace">
    <header class="page-header">
      <h1 class="page-title">文献检索</h1>
      <p class="page-copy">从临床问题出发，建立可复用、可追溯的检索策略。</p>
    </header>

    <LiteratureWorkspaceTabs
      :active-tab="activeTab"
      @select="activeTab = $event"
      @select-result="activeResult = $event"
    />

    <template v-if="activeTab === 'center'">
      <section class="search-workspace" aria-label="检索策略工作区">
        <SearchStrategyBuilder
          :loading="loading"
          :error="error"
          :pico="pico"
          :topic="topic"
          @submit="handleSubmit"
          @pico-change="handlePicoChange"
          @topic-change="topic = $event"
          @clear="clearStrategyInput"
        />
        <SearchDraftPanel
          :query="editableQuery"
          :loading="termsLoading"
          :expanded="expanded"
          :candidate="candidate"
          @query-change="editableQuery = $event"
          @copy="copyQuery"
        />
        <section class="workspace-execution" aria-label="来源范围与检索操作">
          <SourceScopePanel
            :publication-language="publicationLanguage"
            @change="handleSourceChange"
            @language-change="handleLanguageChange"
          />
          <SearchReadinessPanel
            :topic-filled="topicFilled"
            :source-selected="sourceSelected"
            :draft-ready="draftReady"
            :task-loading="taskLoading"
            :task-error="taskError"
            :has-candidate="Boolean(candidate)"
            @save-draft="saveDraft"
            @run-search="runSearch"
          />
        </section>
      </section>
    </template>

    <ResultsView
      v-else-if="activeTab === 'results' && activeResult"
      :key="activeResult.resultId"
      embedded
      :result-id="activeResult.resultId"
      :task-id="activeResult.taskId"
    />
    <section v-else-if="activeTab === 'results'" class="results-empty-workspace" aria-labelledby="results-empty-title">
      <h2 id="results-empty-title">结果展示</h2>
      <p>尚无可用的真实检索结果。请在检索中心完成一次检索后查看结果快照。</p>
    </section>
    <History
      v-else-if="activeTab === 'history'"
      embedded
      @rerun-succeeded="(selection) => { activeResult = selection; activeTab = 'results'; }"
    />
    <RecommendationsView v-else-if="activeTab === 'recommendations'" embedded />
  </main>
</template>

<style scoped>
.literature-workspace {
  max-width: 1480px;
  margin: 0 auto;
  padding: 24px 32px 40px;
  display: grid;
  gap: 16px;
}
.page-header {
  display: grid;
  gap: 4px;
}
.page-title {
  margin: 0;
  color: var(--text-primary, #0f2a43);
  font-size: clamp(1.25rem, 2vw, 1.5rem);
  font-weight: 680;
  letter-spacing: -0.02em;
  line-height: 1.25;
}
.page-copy {
  margin: 0;
  color: var(--text-muted, #64748b);
  font-size: 0.8125rem;
}
.search-workspace {
  display: grid;
  grid-template-columns: minmax(352px, 5fr) minmax(480px, 8fr);
  gap: 16px;
  align-items: stretch;
}
.workspace-execution {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: minmax(0, 5fr) minmax(420px, 8fr);
  align-items: stretch;
  overflow: hidden;
  border: 1px solid var(--border-subtle, #dbe4f0);
  border-radius: 8px;
  background: var(--surface, #fff);
  box-shadow: 0 8px 24px rgb(15 42 67 / 5%);
}
.workspace-execution :deep(.source-panel) {
  padding: 16px;
  border: 0;
}
.workspace-execution :deep(.readiness-panel) {
  padding: 12px 16px;
  border: 0;
  border-left: 1px solid var(--border-subtle, #dbe4f0);
  background: var(--surface-muted, #f8fafc);
}
.results-empty-workspace { display: grid; gap: .5rem; padding: 2rem 1.1rem; border: 1px solid var(--border-subtle, #dbe4f0); border-radius: 8px; background: var(--surface, #fff); color: var(--text-muted, #64748b); text-align: center; box-shadow: var(--shadow-card, 0 2px 8px rgb(15 42 67 / 4%)); }.results-empty-workspace h2,.results-empty-workspace p { margin: 0; }.results-empty-workspace h2 { color: var(--text-primary, #0f2a43); font-size: 1rem; }.results-empty-workspace p { font-size: .88rem; }
:deep(.workspace-tabs) { gap: 0; padding: 0; border: 0; border-radius: 0; background: transparent; }
:deep(.workspace-tab) { min-height: auto; padding: 8px 14px; border: 0; border-bottom: 2px solid transparent; border-radius: 0; background: transparent; color: var(--text-muted, #64748b); font-size: .8125rem; }
:deep(.workspace-tab + .workspace-tab) { border-left: 1px solid var(--border-strong, #cbd5e1); }
:deep(.workspace-tab.active) { border-bottom-color: var(--color-primary, #2563eb); background: transparent; color: var(--color-primary, #2563eb); }
:deep(.workspace-tab[aria-disabled="true"]) { background: transparent; }
@media (max-width: 900px) {
  .search-workspace {
    grid-template-columns: 1fr;
  }
  .workspace-execution {
    grid-column: auto;
    grid-template-columns: 1fr;
  }
  .workspace-execution :deep(.readiness-panel) {
    border-top: 1px solid var(--border-subtle, #dbe4f0);
    border-left: 0;
  }
}
@media (max-width: 640px) {
  .literature-workspace {
    padding: 16px;
    gap: 12px;
  }
  :deep(.workspace-tab) {
    padding-inline: 10px;
  }
}
</style>
