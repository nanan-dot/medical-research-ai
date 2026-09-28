<script setup lang="ts">
import { shallowRef, watch } from "vue";
import type {
  RecommendationMode,
  RecommendationRun,
} from "../../api/recommendations";

const props = defineProps<{
  researchName: string | null;
  researchQuestion: string | null;
  explorationQuery: string;
  resultCount: number | null;
  database: string | null;
  intentId: number | null;
  mode: RecommendationMode;
  candidateCount: number;
  building: RecommendationRun | null;
  hasActive: boolean;
  pending: boolean;
}>();
const emit = defineEmits<{
  "update:mode": [RecommendationMode];
  "update:candidateCount": [number];
  "update:explorationQuery": [string];
  generate: [];
  cancel: [];
}>();
const editingQuery = shallowRef(false);
const queryDraft = shallowRef("");

watch(
  () => props.explorationQuery,
  (value) => {
    if (!editingQuery.value) queryDraft.value = value;
  },
  { immediate: true },
);

function beginQueryEdit(): void {
  queryDraft.value = props.explorationQuery;
  editingQuery.value = true;
}

function saveQueryEdit(): void {
  const nextQuery = queryDraft.value.trim();
  if (!nextQuery) return;
  emit("update:explorationQuery", nextQuery);
  editingQuery.value = false;
}

function cancelQueryEdit(): void {
  queryDraft.value = props.explorationQuery;
  editingQuery.value = false;
}

function modeLabel(mode: RecommendationMode): string {
  return mode === "latest"
    ? "关注最新"
    : mode === "key_evidence"
      ? "关键证据"
      : "综合推荐";
}
</script>

<template>
  <section class="basis" aria-labelledby="recommendation-basis-title">
    <div class="basis-heading">
      <h2 id="recommendation-basis-title">推荐依据</h2>
    </div>
    <div class="basis-kind">
      <span aria-hidden="true"></span>{{ intentId ? "当前研究" : "探索推荐" }}
    </div>
    <div v-if="!editingQuery" class="research-copy">
      <span class="document-icon" aria-hidden="true">▤</span>
      <div class="research-text">
        <p class="question">
          {{ researchName || researchQuestion || "当前检索主题" }}
        </p>
        <p
          v-if="
            researchName &&
            researchQuestion &&
            researchName !== researchQuestion
          "
          class="question-detail"
        >
          {{ researchQuestion }}
        </p>
      </div>
      <button
        v-if="!intentId"
        class="edit-research"
        type="button"
        @click="beginQueryEdit"
      >
        编辑检索
      </button>
    </div>
    <div v-else class="query-editor">
      <label for="exploration-query">探索检索式</label>
      <textarea
        id="exploration-query"
        v-model="queryDraft"
        rows="3"
        maxlength="4000"
        @keyup.esc="cancelQueryEdit"
      />
      <div class="edit-actions">
        <button class="secondary" type="button" @click="cancelQueryEdit">
          取消
        </button>
        <button
          class="save-query"
          type="button"
          :disabled="!queryDraft.trim()"
          @click="saveQueryEdit"
        >
          保存
        </button>
      </div>
    </div>
    <div class="basis-toolbar">
      <div class="source-block">
        <p class="source-note">
          <strong>当前检索：</strong>{{ database || "数据源暂不可用"
          }}<template v-if="resultCount !== null">
            · {{ resultCount }} 篇</template
          >
        </p>
        <p class="source-note">
          <strong>推荐目标：</strong>{{ modeLabel(mode) }}
        </p>
      </div>
      <div class="controls">
        <label
          ><strong>推荐数量</strong>
          <select
            :value="candidateCount"
            aria-label="推荐数量"
            @change="
              emit(
                'update:candidateCount',
                Number(($event.target as HTMLSelectElement).value),
              )
            "
          >
            <option :value="5">5 篇</option>
            <option :value="10">10 篇</option>
            <option :value="20">20 篇</option>
          </select>
        </label>
        <button
          v-if="building && ['queued', 'running'].includes(building.status)"
          class="secondary"
          type="button"
          @click="emit('cancel')"
        >
          取消生成
        </button>
        <button
          class="primary"
          type="button"
          :disabled="
            pending ||
            !!(building && ['queued', 'running'].includes(building.status))
          "
          @click="emit('generate')"
        >
          {{
            building && ["queued", "running"].includes(building.status)
              ? "正在生成…"
              : hasActive
                ? "重新生成推荐"
                : "生成推荐"
          }}
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.basis {
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--surface);
  padding: 14px 16px;
}
.basis-heading h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 700;
}
.basis-kind {
  display: flex;
  align-items: center;
  gap: 9px;
  margin: 10px 4px 7px;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 700;
}
.basis-kind span {
  width: 8px;
  height: 8px;
  border: 5px solid var(--color-primary);
  border-radius: 50%;
}
.research-copy {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 66px;
  padding: 0 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  background: linear-gradient(90deg, #f8fbff, #fff);
}
.document-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 42px;
  height: 42px;
  border-radius: 50%;
  background: #eef5ff;
  color: var(--color-primary);
  font-size: 20px;
}
.research-text {
  min-width: 0;
  flex: 1;
}
.question {
  margin: 0;
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 700;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.question-detail {
  margin: 2px 0 0;
  color: var(--text-muted);
  font-size: 12px;
}
.edit-research {
  flex: none;
  border: 0;
  background: transparent;
  color: var(--color-primary);
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}
.basis-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(440px, 1fr);
  align-items: center;
  gap: 16px;
  margin-top: 12px;
}
.source-block {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}
.source-note {
  margin: 0;
  color: var(--text-muted);
  font-size: 12px;
}
.source-note strong {
  color: var(--text-primary);
}
.controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
  padding-left: 20px;
  border-left: 1px solid var(--border-subtle);
  flex-wrap: wrap;
}
.controls label {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 12px;
  color: var(--text-muted);
}
.controls select,
.primary,
.secondary,
.save-query {
  min-height: 36px;
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text-primary);
  padding: 0 12px;
  font: inherit;
  font-size: 12px;
}
.primary,
.save-query {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--surface);
  cursor: pointer;
}
.primary {
  min-width: 168px;
  padding: 0 18px;
}
.primary:disabled,
.save-query:disabled {
  opacity: 0.6;
  cursor: default;
}
.secondary {
  cursor: pointer;
}
.query-editor {
  display: grid;
  gap: 8px;
  margin: 12px 0;
  color: var(--text-muted);
  font-size: 12px;
}
.query-editor textarea {
  box-sizing: border-box;
  width: 100%;
  resize: vertical;
  padding: 10px;
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  color: var(--text-primary);
  background: var(--surface);
  font: inherit;
  font-size: 13px;
  line-height: 1.6;
}
.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.basis button:focus-visible,
.basis select:focus-visible,
.basis textarea:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 3px;
}
@media (max-width: 900px) {
  .basis-toolbar {
    grid-template-columns: 1fr;
  }
  .controls {
    justify-content: flex-start;
    padding: 12px 0 0;
    border-top: 1px solid var(--border-subtle);
    border-left: 0;
  }
}
@media (max-width: 640px) {
  .basis {
    padding: 14px;
  }
  .research-copy {
    align-items: flex-start;
    flex-wrap: wrap;
    padding: 12px;
  }
  .edit-research {
    margin-left: auto;
  }
  .controls {
    width: 100%;
    gap: 10px;
  }
  .controls select,
  .controls button {
    min-height: 42px;
  }
  .primary {
    flex: 1;
    min-width: 0;
  }
  .controls label {
    width: 100%;
  }
}
</style>
