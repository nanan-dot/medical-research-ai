<script setup lang="ts">
// 文献检索工作空间：从临床问题建立可追溯检索策略。
// 真实管线：parse-query（解析研究问题→候选条件）→ expand-terms（关键词扩展）
// → build-query（构建检索式）→ createTask（执行检索）。所有数据来自真实后端，
// 不伪造检索完成/论文数量/进度。空态与禁用态诚实表达能力边界。
import { computed, onMounted, reactive, shallowRef, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useQueryIntent } from "../../composables/useQueryIntent";
import { useSearchTerms } from "../../composables/useSearchTerms";
import { useSearchStrategy } from "../../composables/useSearchStrategy";
import type {
  StrategyCount,
  StrategyValidation,
} from "../../types/searchStrategy";
import { useStrategyAutosave } from "../../composables/useStrategyAutosave";
import LiteratureWorkspaceTabs from "./LiteratureWorkspaceTabs.vue";
import SearchStrategyBuilder from "./SearchStrategyBuilder.vue";
import SearchDraftPanel from "./SearchDraftPanel.vue";
import SourceScopePanel from "./SourceScopePanel.vue";
import SearchReadinessPanel from "./SearchReadinessPanel.vue";
import ResultsView from "./ResultsView.vue";
import History from "./History.vue";
import { formatSearchChangeNotice } from "./searchChangeNotice";
import RecommendationsView from "../Recommendations/RecommendationsView.vue";
import { MAX_SEARCH_RESULTS } from "../../api/literatureSearch";
import { searchStrategiesApi } from "../../api/searchStrategies";
import StrategyVersionPanel from "./StrategyVersionPanel.vue";
import SearchCenterHeader from "./SearchCenterHeader.vue";
import SearchJourneyProgress from "./SearchJourneyProgress.vue";
import StrategyBasisSection from "./StrategyBasisSection.vue";
import StrategyStickyBar from "./StrategyStickyBar.vue";
import StrategyTermsMeshSection from "./StrategyTermsMeshSection.vue";
import StrategyQuerySection from "./StrategyQuerySection.vue";
import StrategyReadySection from "./StrategyReadySection.vue";
import StrategyLimitsSection from "./StrategyLimitsSection.vue";
import { currentStrategyValidation, strategyReadiness } from "./strategyReadiness";
import { strategyIntent } from "./strategyIntent";

const route = useRoute();
const router = useRouter();

const literatureWorkspaceTabs = [
  "center",
  "results",
  "history",
  "recommendations",
] as const;
type LiteratureWorkspaceTab = (typeof literatureWorkspaceTabs)[number];
type ResultSelection = { resultId: number; taskId: number };

const {
  parsed,
  candidate,
  loading: intentLoading,
  error: intentError,
  parse,
} = useQueryIntent();
const {
  expanded,
  result,
  loading: termsLoading,
  error: termsError,
  taskLoading,
  taskError,
  expand,
  build,
  createTask,
} = useSearchTerms();
const {
  strategy,
  loading: strategyLoading,
  error: strategyLoadError,
  load: loadStrategy,
  refreshMesh,
  addTerm,
  patchTerm,
  deleteTerm,
  remapTerms,
  versions: strategyVersions,
  comparison: strategyComparison,
  loadVersions,
  createVersion,
  compareVersions,
  validate: validateStrategy,
  count: refreshStrategyCount,
} = useSearchStrategy();
const {
  saveState,
  error: autosaveError,
  schedule: scheduleAutosave,
  retry: retryAutosave,
  saveNow,
} = useStrategyAutosave(strategy);

const topic = shallowRef("");
const editableQuery = shallowRef("");
// PICO 受控状态：reactive 保证子组件 emit 后响应式更新。
const pico = reactive({
  population: "",
  intervention: "",
  comparison: "",
  outcome: "",
});
const selectedSources = shallowRef<string[]>(["pubmed"]);
const publicationLanguage = shallowRef<"any" | "chinese">("any");
// URL 是工作区标签页的唯一来源，保证结果页返回和刷新后仍能恢复用户所在上下文。
const activeTab = computed<LiteratureWorkspaceTab>(() => {
  const requestedTab = route.query.tab;
  return typeof requestedTab === "string" &&
    literatureWorkspaceTabs.includes(requestedTab as LiteratureWorkspaceTab)
    ? (requestedTab as LiteratureWorkspaceTab)
    : "center";
});
const activeResult = shallowRef<ResultSelection | null>(null);
const reuseNotice = shallowRef("");
const previousResultId = shallowRef<number | null>(null);
const strategyValidation = shallowRef<StrategyValidation | null>(null);
const strategyCount = shallowRef<StrategyCount | null>(null);
const strategyActionLoading = shallowRef(false);
const strategyActionError = shallowRef<string | null>(null);
const strategyExecutionLoading = shallowRef(false);
const strategyExecutionError = shallowRef<string | null>(null);
const isQuerySynced = computed(() => strategy.value !== null && editableQuery.value === strategy.value.query_text);
const currentValidation = computed(() => strategy.value === null ? null : currentStrategyValidation(strategy.value, editableQuery.value, strategyValidation.value));
const currentCount = computed(() => isQuerySynced.value && strategyCount.value?.fingerprint === strategy.value?.fingerprint ? strategyCount.value : null);
const isPersisting = computed(() => !isQuerySynced.value || ["saving", "failed", "conflict"].includes(saveState.value));
const strategyBusy = computed(() => strategyActionLoading.value || strategyExecutionLoading.value || strategyLoading.value || saveState.value === "saving");
const activeStrategyStep = computed(() => {
  // “开始检索”只在真实 execute 成功后才完成；当前工作台即使已获取
  // Count，仍处于“构建检索策略”阶段，不能把 Count 误展示为执行完成。
  if (strategy.value?.terms.length) return 3;
  if (topic.value.trim()) return 2;
  return 1;
});
const visibleSaveState = computed(() => {
  // 初次恢复视为已保存；编辑后尚未发送的 700ms 也必须如实显示待保存。
  return isQuerySynced.value && saveState.value === "unsaved"
    ? "saved"
    : saveState.value;
});

const loading = computed(() => intentLoading.value || termsLoading.value);
const error = computed(() => intentError.value || termsError.value);

// 顶部栏/工作台跳转时携带的 raw_topic 预填（仅当路由可用时）。
const routeQuery = route?.query;
if (
  routeQuery &&
  typeof routeQuery.raw_topic === "string" &&
  routeQuery.raw_topic
) {
  topic.value = routeQuery.raw_topic;
}

onMounted(async () => {
  const strategyId = Number(route.query.strategy_id);
  if (!Number.isSafeInteger(strategyId) || strategyId <= 0) return;
  // 入口创建策略后会显式传入 strategy_id。该 ID 是用户本次输入问题的
  // 唯一事实来源，不能因策略尚未补全为 PICO 而跳转到另一条旧策略。
  const restored = await loadStrategy(strategyId);
  if (restored === null) return;
  topic.value = restored.research_question;
  editableQuery.value = restored.query_text;
  await loadVersions();
});

watch(editableQuery, (queryText) => {
  strategyValidation.value = null;
  strategyCount.value = null;
  if (strategy.value !== null && queryText !== strategy.value.query_text) {
    scheduleAutosave(queryText);
  }
});

watch(() => strategy.value?.revision, () => {
  strategyValidation.value = null;
  strategyCount.value = null;
});

async function runStrategyAction(action: () => Promise<void>): Promise<void> {
  if (strategyBusy.value || isPersisting.value) return;
  strategyActionLoading.value = true;
  strategyActionError.value = null;
  try {
    await action();
  } catch (caught) {
    strategyActionError.value =
      caught instanceof Error ? caught.message : "策略操作失败，请重试。";
  } finally {
    strategyActionLoading.value = false;
  }
}

function handleMeshRefresh(): void {
  void runStrategyAction(refreshMesh);
}

function handleValidation(): void {
  void runStrategyAction(async () => {
    const revision = strategy.value?.revision;
    const validated = await validateStrategy();
    if (revision === strategy.value?.revision && isQuerySynced.value) strategyValidation.value = validated;
  });
}

function handleCountRefresh(): void {
  void runStrategyAction(async () => {
    const revision = strategy.value?.revision;
    const counted = await refreshStrategyCount();
    if (revision === strategy.value?.revision && isQuerySynced.value) strategyCount.value = counted;
  });
}

function handleVersionCreate(): void {
  void runStrategyAction(createVersion);
}

function handleVersionCompare(fromVersion: number, toVersion: number): void {
  void runStrategyAction(async () => {
    await compareVersions(fromVersion, toVersion);
  });
}

function handleTermAdd(payload: { text: string; conceptGroup: string }): void {
  void runStrategyAction(async () => {
    await addTerm({ text: payload.text, concept_group: payload.conceptGroup });
  });
}

function handleTermLock(termId: number, isLocked: boolean): void {
  void runStrategyAction(async () => {
    await patchTerm(termId, { is_locked: isLocked });
  });
}

function handleTermDelete(termId: number): void {
  void runStrategyAction(async () => {
    await deleteTerm(termId);
  });
}

function handleTermRemap(): void {
  void runStrategyAction(remapTerms);
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

function handlePicoChange(next: {
  population: string;
  intervention: string;
  comparison: string;
  outcome: string;
}): void {
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
  if (strategy.value === null || !editableQuery.value.trim()) return;
  void saveNow(editableQuery.value);
}

function handleStrategyRegenerate(): void {
  if (strategy.value === null) return;
  void router.push({
    path: "/literature-search",
    query: { raw_topic: strategy.value.research_question },
  });
}

function copyQuery(): void {
  if (editableQuery.value)
    void window.navigator.clipboard?.writeText(editableQuery.value);
}

function selectTab(nextTab: LiteratureWorkspaceTab): void {
  const nextQuery = { ...route.query };
  if (nextTab === "center") {
    delete nextQuery.tab;
  } else {
    nextQuery.tab = nextTab;
  }
  void router.replace({ query: nextQuery });
}

function showResult(selection: ResultSelection): void {
  activeResult.value = selection;
  selectTab("results");
}

// 执行检索：真实 createTask（调用后端 PubMed 检索），成功后在本页面切换至结果展示。
async function runSearch(): Promise<void> {
  if (strategy.value !== null) {
    if (!draftReady.value) return;
    strategyExecutionLoading.value = true;
    strategyExecutionError.value = null;
    try {
      const executed = await searchStrategiesApi.execute(strategy.value.id);
      await router.push(`/literature-search/results/${executed.new_result_id || executed.latest_result_id}`);
    } catch (caught) {
      strategyExecutionError.value =
        caught instanceof Error
          ? caught.message
          : "策略执行失败，请修正后重试。";
    } finally {
      strategyExecutionLoading.value = false;
    }
    return;
  }
  if (!result.value || !parsed.value || !editableQuery.value.trim()) return;
  reuseNotice.value = "";
  previousResultId.value = null;
  const created = await createTask({
    original_query: parsed.value.raw_topic,
    structured_query: JSON.stringify(parsed.value.candidate),
    search_string:
      publicationLanguage.value === "chinese"
        ? `(${editableQuery.value}) AND chinese[la]`
        : editableQuery.value,
    filters: JSON.stringify({
      publication_language: publicationLanguage.value,
    }),
    model_version: parsed.value.prompt_version,
    user_edits: JSON.stringify(result.value.user_edits),
    retmax: MAX_SEARCH_RESULTS,
  });
  if (created !== null && created.latest_result_id !== null) {
    // 部署滚动更新期间，旧后端尚未返回 new_result_id；其 latest_result_id
    // 同样指向本次成功快照，回退可避免把 undefined 传入结果页。
    const resultId = created.new_result_id || created.latest_result_id;
    activeResult.value = { resultId, taskId: created.id };
    if (created.operation === "reused") {
      const latestVersion = created.versions.at(-1);
      const priorVersion = created.versions.at(-2);
      if (latestVersion) {
        reuseNotice.value = formatSearchChangeNotice(created.change) ?? "";
        previousResultId.value = priorVersion?.result_id ?? null;
      }
    }
    selectTab("results");
  }
}

const topicFilled = computed(() => topic.value.trim().length > 0);
const sourceSelected = computed(() => selectedSources.value.length > 0);
// Recovered server drafts are executable even when this browser has not run the
// legacy parse/expand/build sequence during the current page lifetime.
const draftReady = computed(() =>
  strategy.value !== null
    ? !strategyBusy.value && !isPersisting.value && strategyReadiness(strategy.value, editableQuery.value, strategyValidation.value).canExecute
    : Boolean(editableQuery.value.trim() && result.value?.boolean_query),
);
</script>

<template>
  <main class="literature-workspace">
    <SearchCenterHeader
      :save-state="visibleSaveState"
      :versions="strategyVersions"
      :executing="strategyExecutionLoading"
      :can-execute="draftReady"
      @create-version="handleVersionCreate"
      @execute="runSearch"
    />
    <SearchJourneyProgress
      :active-step="activeStrategyStep"
      :intent-confirmed="strategy ? strategyIntent(strategy).complete : Boolean(parsed)"
    />
    <p
      v-if="reuseNotice"
      class="reuse-notice"
      role="status"
    >
      {{ reuseNotice }}
      <RouterLink
        v-if="previousResultId"
        :to="`/literature-search/results/${previousResultId}`"
      >
        查看上次结果 →
      </RouterLink>
    </p>
    <p
      v-if="strategyLoading"
      class="strategy-status"
      role="status"
    >
      正在恢复已保存的检索策略…
    </p>
    <p
      v-else-if="strategyLoadError"
      class="strategy-error"
      role="alert"
    >
      {{ strategyLoadError }}
    </p>
    <StrategyBasisSection
      v-if="strategy"
      :strategy="strategy"
      @regenerate="handleStrategyRegenerate"
    />
    <p
      v-if="saveState === 'saving'"
      class="strategy-status"
      role="status"
    >
      正在保存策略…
    </p>
    <p
      v-else-if="saveState === 'saved'"
      class="strategy-status"
      role="status"
    >
      策略已保存
    </p>
    <p
      v-else-if="autosaveError"
      class="strategy-error"
      role="alert"
    >
      {{ autosaveError }}
      <button
        type="button"
        @click="retryAutosave"
      >
        重试
      </button>
    </p>

    <template v-if="strategy">
      <StrategyTermsMeshSection
        :terms="strategy.terms"
        :mesh-terms="strategy.mesh_terms"
        :loading="strategyBusy || isPersisting"
        @add="handleTermAdd"
        @lock="handleTermLock"
        @remove="handleTermDelete"
        @remap="handleTermRemap"
        @refresh-mesh="handleMeshRefresh"
      />
      <StrategyQuerySection
        v-model="editableQuery"
        :strategy="strategy"
        :validation="currentValidation"
        :count="currentCount"
        :loading="strategyBusy"
        :actions-disabled="isPersisting"
        @copy="copyQuery"
        @validate="handleValidation"
        @refresh-count="handleCountRefresh"
      />
      <div class="workspace-status-grid">
        <StrategyLimitsSection
          :strategy="strategy"
          @edit="handleStrategyRegenerate"
        />
        <StrategyReadySection
          :strategy="strategy"
          :validation="strategyValidation"
          :query-text="editableQuery"
          :count-available="currentCount !== null"
          :action-error="strategyActionError || strategyExecutionError"
        />
      </div>
      <StrategyVersionPanel
        :versions="strategyVersions"
        :comparison="strategyComparison"
        :loading="strategyActionLoading"
        :error="strategyActionError"
        @create-version="handleVersionCreate"
        @compare="handleVersionCompare"
      />
    </template>

    <LiteratureWorkspaceTabs
      :active-tab="activeTab"
      @select="selectTab"
      @select-result="showResult"
    />

    <template v-if="activeTab === 'center' && !strategy">
      <section
        id="strategy-question"
        class="search-workspace"
        aria-label="检索策略工作区"
      >
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
        <section
          id="strategy-execute"
          class="workspace-execution"
          aria-label="来源范围与检索操作"
        >
          <SourceScopePanel
            :publication-language="publicationLanguage"
            @change="handleSourceChange"
            @language-change="handleLanguageChange"
          />
          <SearchReadinessPanel
            :topic-filled="topicFilled"
            :source-selected="sourceSelected"
            :draft-ready="draftReady"
            :task-loading="taskLoading || strategyExecutionLoading"
            :task-error="strategyExecutionError || taskError"
            :has-candidate="Boolean(candidate) || strategy !== null"
            @save-draft="saveDraft"
            @run-search="runSearch"
          />
        </section>
      </section>
    </template>
    <StrategyStickyBar
      v-if="activeTab === 'center' && strategy"
      :strategy="strategy"
      :versions="strategyVersions"
      :save-state="visibleSaveState"
      :executing="strategyExecutionLoading"
      :disabled="!draftReady"
      @execute="runSearch"
    />

    <ResultsView
      v-else-if="activeTab === 'results' && activeResult"
      :key="activeResult.resultId"
      embedded
      :result-id="activeResult.resultId"
      :task-id="activeResult.taskId"
    />
    <section
      v-else-if="activeTab === 'results'"
      class="results-empty-workspace"
      aria-labelledby="results-empty-title"
    >
      <h2 id="results-empty-title">结果展示</h2>
      <p>尚无可用的真实检索结果。请在检索中心完成一次检索后查看结果快照。</p>
    </section>
    <History
      v-else-if="activeTab === 'history'"
      embedded
      @rerun-succeeded="showResult"
    />
    <RecommendationsView
      v-else-if="activeTab === 'recommendations'"
      embedded
    />
  </main>
</template>

<style scoped>
.literature-workspace {
  min-width: 0;
  box-sizing: border-box;
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0 0 40px;
  display: grid;
  gap: 0;
}
.literature-workspace:has(.strategy-sticky) {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  padding-bottom: 0;
}
.literature-workspace:has(.strategy-sticky) > .strategy-sticky {
  margin-top: auto;
  flex: 0 0 auto;
}
.literature-workspace:has(.strategy-sticky) :deep(.strategy-version-panel),
.literature-workspace:has(.strategy-sticky) :deep(.workspace-tabs) {
  display: none;
}
.page-header {
  display: grid;
  gap: 4px;
}
.page-title {
  margin: 0;
  color: var(--text-primary, #0f2a43);
  font-size: clamp(1.75rem, 2.5vw, 2rem);
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.25;
}
.page-copy {
  margin: 0;
  color: var(--text-muted, #64748b);
  font-size: 0.8125rem;
}
.reuse-notice {
  margin: 0;
  padding: 0.7rem 0.9rem;
  border-radius: 8px;
  background: var(--color-success-soft, #ecfdf5);
  color: var(--color-success, #047857);
  font-size: 0.9rem;
}
.literature-workspace
  > :not(.search-center-header):not(.journey):not(.strategy-sticky) {
  margin-inline: 24px;
}
.strategy-status,
.strategy-error {
  margin: 0;
  font-size: 0.82rem;
}
.strategy-status {
  color: var(--color-success, #047857);
}
.strategy-error {
  color: var(--color-danger, #b42318);
}
.literature-workspace > .terms-mesh-section,
.literature-workspace > .strategy-query,
.literature-workspace > .strategy-version-panel {
  margin-top: 10px;
}
.workspace-status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 10px;
  margin-bottom: 11px;
}
.workspace-status-grid > .strategy-limits,
.workspace-status-grid > .strategy-ready {
  margin-top: 1px;
}
@media (min-width: 1025px) {
  .workspace-status-grid > .strategy-limits,
  .workspace-status-grid > .strategy-ready {
    box-sizing: border-box;
    min-height: 80px;
    padding: 12px 20px;
  }
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
.results-empty-workspace {
  display: grid;
  gap: 0.5rem;
  padding: 2rem 1.1rem;
  border: 1px solid var(--border-subtle, #dbe4f0);
  border-radius: 8px;
  background: var(--surface, #fff);
  color: var(--text-muted, #64748b);
  text-align: center;
  box-shadow: var(--shadow-card, 0 2px 8px rgb(15 42 67 / 4%));
}
.results-empty-workspace h2,
.results-empty-workspace p {
  margin: 0;
}
.results-empty-workspace h2 {
  color: var(--text-primary, #0f2a43);
  font-size: 1rem;
}
.results-empty-workspace p {
  font-size: 0.88rem;
}
:deep(.workspace-tabs) {
  gap: 0;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
}
:deep(.workspace-tab) {
  min-height: auto;
  padding: 8px 14px;
  border: 0;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  background: transparent;
  color: var(--text-muted, #64748b);
  font-size: 0.8125rem;
}
:deep(.workspace-tab + .workspace-tab) {
  border-left: 1px solid var(--border-strong, #cbd5e1);
}
:deep(.workspace-tab.active) {
  border-bottom-color: var(--color-primary, #2563eb);
  background: transparent;
  color: var(--color-primary, #2563eb);
}
:deep(.workspace-tab[aria-disabled="true"]) {
  background: transparent;
}
@media (max-width: 1440px) {
  .literature-workspace {
    padding-bottom: 32px;
  }
}
@media (max-width: 1280px) {
  .search-workspace {
    grid-template-columns: minmax(320px, 5fr) minmax(380px, 8fr);
  }
  .workspace-execution {
    grid-template-columns: minmax(0, 1fr) minmax(340px, 1fr);
  }
}
@media (max-width: 1120px) {
  .search-workspace {
    grid-template-columns: 1fr;
  }
  .workspace-execution {
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
  }
  .literature-workspace:has(.strategy-sticky) {
    min-height: auto;
  }
  .literature-workspace
    > :not(.search-center-header):not(.journey):not(.strategy-sticky) {
    margin-inline: 0;
  }
  :deep(.workspace-tab) {
    padding-inline: 10px;
  }
}
@media (max-width: 1024px) {
  .workspace-status-grid {
    grid-template-columns: 1fr;
  }
}
</style>
