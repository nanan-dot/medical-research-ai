<script setup lang="ts">
import { computed, ref, shallowRef, watch } from "vue";
import { useRoute } from "vue-router";
import {
  literatureSearchApi,
  type LiteratureSearchTask,
} from "../../api/literatureSearch";
import type {
  DismissReason,
  RecommendationItem,
  RecommendationMode,
} from "../../api/recommendations";
import { useRecommendationsV5 } from "../../composables/useRecommendations";
import RecommendationHeader from "../../components/recommendations/RecommendationHeader.vue";
import RecommendationBasisPanel from "../../components/recommendations/RecommendationBasisPanel.vue";
import RecommendationListItem from "../../components/recommendations/RecommendationListItem.vue";
import RecommendationPagination from "../../components/recommendations/RecommendationPagination.vue";
import RecommendationSkeleton from "../../components/recommendations/RecommendationSkeleton.vue";
import RecommendationExplanationDrawer from "../../components/recommendations/RecommendationExplanationDrawer.vue";
import RecommendationHistoryDrawer from "../../components/recommendations/RecommendationHistoryDrawer.vue";
import RecommendationDismissDialog from "../../components/recommendations/RecommendationDismissDialog.vue";
const route = useRoute();
const resultId = ref<number | null>(positive(route.query.result_id));
const routeIntentId = ref<number | null>(
  positive(route.query.intent_snapshot_id),
);
const task = shallowRef<LiteratureSearchTask | null>(null);
const explorationQuery = shallowRef<string | null>(null);
const contextLoading = ref(true);
const mode = ref<RecommendationMode>("balanced");
const candidateCount = ref(10);
const historyOpen = ref(false);
const explanationOpen = ref(false);
const dismissOpen = ref(false);
const selected = shallowRef<RecommendationItem | null>(null);
const returnFocus = shallowRef<HTMLElement | null>(null);
const decisionPending = ref(false);
const decisionError = ref<string | null>(null);
const r = useRecommendationsV5(resultId, routeIntentId);
const researchQuestion = computed(() => task.value?.original_query ?? null);
const researchName = computed(() =>
  r.intentSnapshotId.value
    ? (r.page.value?.research_name ?? researchQuestion.value)
    : (explorationQuery.value ??
      r.active.value?.exploration_query ??
      researchQuestion.value),
);
const needsRegeneration = computed(
  () =>
    r.active.value?.warnings.includes(
      "recommendation_quality_upgrade_required",
    ) ?? false,
);
function positive(value: unknown): number | null {
  const raw = Array.isArray(value) ? value[0] : value;
  const parsed = Number(raw);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}
function warningText(value: string): string {
  return value === "recommendation_quality_upgrade_required"
    ? "旧版结果尚未经过主题匹配核验，请重新生成推荐。"
    : value === "query_relaxed_to_meet_requested_count"
      ? "严格检索结果不足，已在保持疾病与干预措施匹配的前提下放宽次要条件补充候选。"
      : value === "novel_candidates_below_requested_count"
        ? "新增候选数量少于请求数量，其余候选已被当前检索结果覆盖或不满足推荐条件。"
        : value;
}
let contextGeneration = 0;
async function resolveContext() {
  const current = ++contextGeneration;
  contextLoading.value = true;
  try {
    const history = await literatureSearchApi.listHistory(0, 100);
    if (current !== contextGeneration) return;
    const match = resultId.value
      ? history.items.find((item) => item.latest_result_id === resultId.value)
      : history.items.find(
          (item) => item.status === "succeeded" && item.latest_result_id,
        );
    if (!resultId.value && match?.latest_result_id)
      resultId.value = match.latest_result_id;
    if (match) {
      const nextTask = await literatureSearchApi.getTask(match.id);
      if (current === contextGeneration) {
        task.value = nextTask;
        if (!explorationQuery.value)
          explorationQuery.value = nextTask.original_query;
        if (routeIntentId.value && !nextTask.research_context_id) {
          routeIntentId.value = null;
          r.notice.value =
            "当前结果尚未绑定研究上下文，已忽略旧链接中的研究意图；本次将基于当前检索快照生成探索推荐。";
        }
      }
    } else if (current === contextGeneration) {
      task.value = null;
      if (routeIntentId.value) {
        routeIntentId.value = null;
        r.notice.value =
          "未找到当前结果所属的检索任务，已忽略旧链接中的研究意图。";
      }
    }
  } catch {
    if (current === contextGeneration) task.value = null;
  } finally {
    if (current === contextGeneration) contextLoading.value = false;
  }
}
function openHistory(trigger: HTMLElement) {
  returnFocus.value = trigger;
  historyOpen.value = true;
}
function openExplanation(
  item: RecommendationItem,
  trigger: HTMLElement | null,
) {
  selected.value = item;
  returnFocus.value = trigger;
  explanationOpen.value = true;
}
function openDismiss(
  item: RecommendationItem,
  _reason: DismissReason,
  trigger: HTMLElement | null,
) {
  selected.value = item;
  returnFocus.value = trigger;
  decisionError.value = null;
  dismissOpen.value = true;
}
async function accept(item: RecommendationItem) {
  try {
    await r.decide(item, "accepted");
  } catch (e) {
    r.error.value = e instanceof Error ? e.message : "加入候选失败";
  }
}
async function confirmDismiss(reason: DismissReason) {
  if (!selected.value) return;
  decisionPending.value = true;
  decisionError.value = null;
  try {
    await r.decide(selected.value, "dismissed", reason);
    dismissOpen.value = false;
  } catch (e) {
    decisionError.value = e instanceof Error ? e.message : "忽略推荐失败";
  } finally {
    decisionPending.value = false;
  }
}
watch(
  () => [route.query.result_id, route.query.intent_snapshot_id],
  ([nextResult, nextIntent]) => {
    const parsedResult = positive(nextResult);
    const parsedIntent = positive(nextIntent);
    resultId.value = parsedResult;
    routeIntentId.value = parsedIntent;
    task.value = null;
    explorationQuery.value = null;
    historyOpen.value = false;
    explanationOpen.value = false;
    dismissOpen.value = false;
    void resolveContext();
  },
  { immediate: true },
);
</script>
<template>
  <main class="page">
    <RecommendationHeader
      @history="openHistory($event)"
    /><RecommendationBasisPanel
      :research-name="researchName"
      :research-question="researchQuestion"
      :exploration-query="researchName ?? ''"
      :result-count="task?.result_count ?? null"
      :database="task?.database ?? null"
      :intent-id="r.intentSnapshotId.value"
      :mode="mode"
      :candidate-count="candidateCount"
      :building="r.building.value"
      :has-active="r.active.value !== null"
      :pending="r.actionPending.value"
      @update:exploration-query="explorationQuery = $event"
      @update:mode="mode = $event"
      @update:candidate-count="candidateCount = $event"
      @generate="
        r.createRun(mode, candidateCount, explorationQuery ?? researchQuestion)
      "
      @cancel="r.cancel"
    />
    <div v-if="r.isNarrating.value" class="notice" role="status">
      推荐已生成，正在优化表述
    </div>
    <div
      v-else-if="
        r.active.value?.narration_status?.startsWith('fallback_') ||
        r.active.value?.narration_status === 'completed_with_fallback'
      "
      class="notice"
      role="status"
    >
      当前展示可核验的标准理由；部分表述优化未采用
    </div>
    <div v-if="r.notice.value" class="notice" role="status">
      {{ r.notice.value }}
    </div>
    <div v-if="r.error.value" class="error" role="alert">
      <span>{{ r.error.value }}</span
      ><button type="button" @click="r.initialize">重试</button>
    </div>
    <section class="results" aria-labelledby="results-title">
      <header>
        <div class="summary">
          <h2 id="results-title">推荐结果</h2>
          <template v-if="r.page.value">
            <span>{{ r.page.value.novel_count }}篇新增候选</span>
            <button
              v-if="r.page.value.covered_count > 0"
              type="button"
              :aria-pressed="r.overlap.value === 'covered'"
              @click="
                r.overlap.value =
                  r.overlap.value === 'novel' ? 'covered' : 'novel'
              "
            >
              {{
                r.overlap.value === "novel"
                  ? `另有${r.page.value.covered_count}篇已在当前结果中`
                  : `${r.page.value.covered_count}篇已在当前结果中 · 返回新增候选`
              }}
            </button>
          </template>
        </div>
        <label v-if="r.page.value"
          >排序：<select v-model="r.sort.value">
            <option value="priority">推荐优先</option>
            <option value="created">生成时间</option>
          </select></label
        >
      </header>
      <div v-if="r.active.value?.warnings.length" class="warning" role="status">
        {{ r.active.value.warnings.map(warningText).join("；") }}
      </div>
      <RecommendationSkeleton
        v-if="(r.loading.value || r.isBuilding.value) && !r.page.value"
      />
      <div v-else-if="needsRegeneration" class="empty">
        <h3>推荐依据已升级</h3>
        <p>
          这组旧版结果缺少逐篇主题匹配核验。重新生成后将按实际检索条件筛选，并展示具体依据。
        </p>
        <button
          type="button"
          :disabled="r.isBuilding.value"
          @click="
            r.createRun(
              mode,
              candidateCount,
              explorationQuery ?? researchQuestion,
            )
          "
        >
          重新生成推荐
        </button>
      </div>
      <div v-else-if="!resultId && !contextLoading" class="empty">
        <h3>请先完成一次文献检索</h3>
        <p>推荐需要绑定真实检索结果。</p>
        <RouterLink to="/literature-search">返回检索中心</RouterLink>
      </div>
      <div
        v-else-if="r.building.value?.status === 'failed' && !r.page.value"
        class="empty error-empty"
      >
        <h3>推荐生成失败</h3>
        <p>
          {{ r.building.value.last_error?.message || "本轮未生成可用版本。" }}
        </p>
        <button type="button" @click="r.createRun(mode, candidateCount)">
          重新生成
        </button>
      </div>
      <div
        v-else-if="r.building.value?.status === 'cancelled' && !r.page.value"
        class="empty"
      >
        <h3>推荐生成已取消</h3>
        <p>可以保留当前设置重新生成。</p>
        <button type="button" @click="r.createRun(mode, candidateCount)">
          重新生成
        </button>
      </div>
      <div v-else-if="r.page.value && !r.page.value.items.length" class="empty">
        <h3>
          {{
            r.overlap.value === "novel"
              ? "暂无通过匹配核验的新增文献"
              : "没有已覆盖文献"
          }}
        </h3>
        <p>
          {{
            r.overlap.value === "novel"
              ? "本轮没有找到同时满足检索条件且不在现有集合中的文献。可查看已覆盖文献，或编辑检索条件。"
              : "当前活动版本没有返回已覆盖条目。"
          }}
        </p>
      </div>
      <div v-else-if="!r.page.value && !r.loading.value" class="empty">
        <h3>
          {{ r.intentSnapshotId.value ? "尚未生成推荐" : "可生成探索推荐" }}
        </h3>
        <p>
          {{
            r.intentSnapshotId.value
              ? "可生成一组可核验的增量文献候选。"
              : "可依据当前真实检索式生成相关论文候选；确认研究意图后会获得更针对性的推荐。"
          }}
        </p>
      </div>
      <template v-else-if="r.page.value"
        ><ol class="list" :aria-busy="r.syncing.value">
          <RecommendationListItem
            v-for="item in r.page.value.items"
            :key="item.pmid"
            :item="item"
            @accept="accept"
            @dismiss="openDismiss"
            @explanation="openExplanation"
          />
        </ol>
        <RecommendationPagination
          :page="r.currentPage.value"
          :total-pages="r.totalPages.value"
          :total="r.page.value.total"
          :pending="r.syncing.value"
          @change="r.goToPage"
      /></template>
    </section>
    <RecommendationExplanationDrawer
      :open="explanationOpen"
      :result-id="resultId"
      :run-id="r.page.value?.run_id ?? null"
      :pmid="selected?.pmid ?? null"
      :return-focus="returnFocus"
      @close="explanationOpen = false"
    /><RecommendationHistoryDrawer
      :open="historyOpen"
      :result-id="resultId"
      :return-focus="returnFocus"
      @close="historyOpen = false"
    /><RecommendationDismissDialog
      :open="dismissOpen"
      :pending="decisionPending"
      :error="decisionError"
      :return-focus="returnFocus"
      @close="dismissOpen = false"
      @confirm="confirmDismiss"
    />
  </main>
</template>
<style scoped>
.page {
  display: grid;
  gap: 10px;
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  box-sizing: border-box;
  padding: 18px 24px 32px;
  background: var(--page-bg);
  color: var(--text-primary);
}
.results {
  overflow: hidden;
  border: 1px solid #dce5f0;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 1px 2px rgb(15 23 42/0.03);
}
.results > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 54px;
  padding: 0 16px;
  border-bottom: 1px solid #dce5f0;
}
.summary {
  display: flex;
  align-items: center;
  gap: 16px;
}
.summary h2 {
  margin: 0;
  color: #0b2349;
  font-size: 16px;
}
.summary span {
  padding: 3px 8px;
  border-radius: 5px;
  background: #f5f8fc;
  color: #234875;
  font-size: 11px;
}
.summary button {
  border: 0;
  background: transparent;
  color: #274e82;
  font-size: 11px;
  cursor: pointer;
}
.results > header label {
  color: #29466f;
  font-size: 11px;
  font-weight: 700;
}
.results select {
  height: 34px;
  padding: 0 9px;
  border: 1px solid #d7e3f1;
  border-radius: 6px;
  background: #fff;
  color: #193b6d;
}
.notice,
.error,
.warning {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  border: 1px solid #d9e6f5;
  border-radius: 7px;
  background: #eef6ff;
  color: #195087;
  font-size: 12px;
}
.error {
  border-color: #f0c5c1;
  background: #fff4f3;
  color: #b42318;
}
.error button {
  border: 1px solid currentColor;
  border-radius: 5px;
  background: #fff;
  color: inherit;
}
.warning {
  border: 0;
  border-bottom: 1px solid #f0dda5;
  border-radius: 0;
  background: #fff9e9;
  color: #845700;
}
.list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.empty {
  padding: 44px 20px;
  text-align: center;
  color: #475569;
}
.empty h3 {
  margin: 0 0 7px;
  color: #17345f;
  font-size: 15px;
}
.empty p {
  margin: 0 0 12px;
  font-size: 12px;
}
.empty a,
.empty button {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid #d3e0f0;
  border-radius: 7px;
  background: #fff;
  color: #0b5fcc;
  text-decoration: none;
}
.error-empty h3 {
  color: #b42318;
}
@media (max-width: 640px) {
  .page {
    padding: 12px;
    gap: 12px;
  }
  .results > header {
    align-items: stretch;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
  }
  .summary {
    align-items: flex-start;
    flex-direction: column;
    gap: 5px;
  }
  .summary button {
    min-height: 36px;
  }
  .results > header label {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .results select {
    min-height: 44px;
  }
}
</style>
