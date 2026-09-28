<script setup lang="ts">
import { computed, shallowRef, useTemplateRef } from "vue";

import BaseIcon from "../../components/ui/BaseIcon.vue";
import type {
  SearchStrategyMeshTerm,
  SearchStrategyTerm,
} from "../../types/searchStrategy";

const props = defineProps<{
  terms: SearchStrategyTerm[];
  meshTerms: SearchStrategyMeshTerm[];
  loading: boolean;
}>();

const emit = defineEmits<{
  add: [payload: { text: string; conceptGroup: string }];
  lock: [termId: number, isLocked: boolean];
  remove: [termId: number];
  remap: [];
  refreshMesh: [];
}>();

const addDialog = useTemplateRef<HTMLDialogElement>("addDialog");
const addButton = useTemplateRef<HTMLButtonElement>("addButton");
function openAddDialog(): void { addDialog.value?.showModal?.(); }
function closeAddDialog(): void { addDialog.value?.close?.(); addButton.value?.focus(); }
const isShowingAll = shallowRef(false);
const isWarningExpanded = shallowRef(false);
const newTerm = shallowRef("");

const groupDefinitions = [
  { key: "disease", label: "疾病概念", relation: "核心概念" },
  { key: "intervention", label: "干预概念", relation: "药物" },
  { key: "outcome", label: "结局概念", relation: "核心结局" },
  { key: "custom", label: "自定义", relation: "手动添加" },
] as const;

const groupDefinitionByKey = new Map<string, (typeof groupDefinitions)[number]>(
  groupDefinitions.map((definition) => [definition.key, definition]),
);

const normalizedGroup = (value: string): string =>
  ({
    disease: "disease",
    population: "disease",
    "疾病概念": "disease",
    "疾病": "disease",
    intervention: "intervention",
    comparison: "intervention",
    "干预概念": "intervention",
    "干预": "intervention",
    outcome: "outcome",
    "结局概念": "outcome",
    "结局": "outcome",
  })[value] ?? value;

type MeshVerificationStatus = SearchStrategyMeshTerm["verification_status"];

const meshStatusPriority: Record<MeshVerificationStatus, number> = {
  verified: 0,
  not_found: 1,
  stale: 2,
  unavailable: 3,
};

function meshStatusForGroup(groupKey: string): MeshVerificationStatus | null {
  // 同一概念组存在多条官方候选时，优先呈现最需要用户处理的状态，避免一条
  // 已验证候选掩盖同组其余候选的不可用或过期状态。
  const statuses = props.meshTerms
    .filter((term) => normalizedGroup(term.concept_group) === groupKey)
    .map((term) => term.verification_status);
  return statuses.reduce<MeshVerificationStatus | null>(
    (current, status) =>
      current === null ||
      meshStatusPriority[status] > meshStatusPriority[current]
        ? status
        : current,
    null,
  );
}

const groups = computed(() => {
  const termsByGroup = new Map<string, SearchStrategyTerm[]>();
  for (const term of props.terms) {
    const groupKey = normalizedGroup(term.concept_group);
    termsByGroup.set(groupKey, [...(termsByGroup.get(groupKey) ?? []), term]);
  }

  const knownGroups = groupDefinitions.flatMap((definition) => {
    const terms = termsByGroup.get(definition.key) ?? [];
    return terms.length
      ? [{ ...definition, originalGroup: "", terms, meshStatus: meshStatusForGroup(definition.key) }]
      : [];
  });
  // 未知分类保留各自来源和 MeSH 状态，不把它们错误合并为同一概念。
  const otherGroups = [...termsByGroup.entries()]
    .filter(([key]) => !groupDefinitionByKey.has(key))
    .map(([key, terms]) => ({
      key: `other:${key}`, originalGroup: key, label: "其他术语",
      relation: "原始分类", terms, meshStatus: meshStatusForGroup(key),
    }));
  return [...knownGroups, ...otherGroups];
});
const visibleGroups = computed(() =>
  groups.value.map((group) => ({
    ...group,
    totalCount: group.terms.length,
    terms: isShowingAll.value ? group.terms : group.terms.slice(0, 3),
  })),
);

const visibleMeshTerms = computed(() =>
  isShowingAll.value ? props.meshTerms : props.meshTerms.slice(0, 5),
);
const lockedCount = computed(
  () => props.terms.filter((term) => term.is_locked).length,
);
const warningTerms = computed(() => props.terms.filter((term) => term.warning));
const firstWarning = computed(() => warningTerms.value[0]?.warning ?? null);
const coverageNotice = computed(() => {
  if (props.terms.length === 0) {
    return {
      title: "尚未生成检索术语",
      message: "请返回上一步补充研究问题，或手动添加术语后再进行映射。",
    };
  }

  const covered = new Set<string>(
    groups.value
      .map((group) => group.key)
      .filter((key) => ["disease", "intervention", "outcome"].includes(key)),
  );
  if (covered.size >= 2) return null;
  if (covered.size === 0) {
    return {
      title: "尚未识别标准概念",
      message: "当前术语尚未归入疾病、干预或结局概念；请编辑研究问题或手动补充术语。",
    };
  }
  if (covered.has("intervention")) {
    return {
      title: "概念覆盖不足",
      message: "当前仅识别到干预概念；补充疾病或结局后，可重新映射术语。",
    };
  }
  if (covered.has("outcome")) {
    return {
      title: "概念覆盖不足",
      message: "当前仅识别到结局概念；补充疾病或干预后，可重新映射术语。",
    };
  }
  return {
    title: "概念覆盖不足",
    message: "当前仅识别到疾病概念；补充干预、结局或研究类型后，可重新映射术语。",
  };
});

function addTerm(): void {
  const text = newTerm.value.trim();
  if (!text) return;
  emit("add", { text, conceptGroup: "custom" });
  newTerm.value = "";
  closeAddDialog();
}

function sourceLabel(source: SearchStrategyTerm["source"]): string {
  return {
    research_question: "问题提取",
    smart_expansion: "智能扩展",
    user_added: "手动添加",
  }[source];
}

function relationLabel(relation: string | null, fallback: string): string {
  if (!relation) return fallback;
  return ({ core: "核心概念", synonym: "同义词", broader: "上位词", narrower: "下位词", related: "相关词" } as Record<string, string>)[relation] ?? relation;
}

function meshStatusLabel(
  status: SearchStrategyMeshTerm["verification_status"],
): string {
  return {
    verified: "NLM MeSH",
    not_found: "未找到",
    unavailable: "暂不可用",
    stale: "需刷新",
  }[status];
}

function groupMeshStatusLabel(status: MeshVerificationStatus | null): string {
  if (status === null) return "MeSH 未查询";
  return {
    verified: "MeSH 已验证",
    not_found: "MeSH 未找到",
    unavailable: "MeSH 暂不可用",
    stale: "MeSH 需刷新",
  }[status];
}
</script>

<template>
  <section
    class="terms-mesh-section"
    :class="{ 'has-multiple-concepts': groups.length > 1 }"
    aria-labelledby="terms-mesh-title"
  >
    <header class="section-heading">
      <div class="heading-copy">
        <div class="title-row">
          <BaseIcon
            name="sync"
            class="section-icon"
          />
          <h2 id="terms-mesh-title">术语与 MeSH</h2>
          <BaseIcon
            name="info"
            class="info-icon"
          />
        </div>
        <p class="statistics">
          <span><BaseIcon name="document" />{{ props.terms.length }} 个检索术语</span>
          <span><BaseIcon name="info" />{{ props.meshTerms.length }} 个 NLM MeSH</span>
          <span><BaseIcon name="lock" />{{ lockedCount }} 个锁定词</span>
        </p>
        <p
          v-if="coverageNotice"
          class="coverage-notice"
          role="status"
        >
          <BaseIcon name="info" />
          <strong>{{ coverageNotice.title }}</strong>
          <span>{{ coverageNotice.message }}</span>
        </p>
      </div>
      <div class="heading-actions">
        <button
          type="button"
          :disabled="props.loading"
          @click="emit('remap')"
        >
          重新映射术语
        </button>
        <button
          type="button"
          :disabled="props.loading"
          @click="emit('refreshMesh')"
        >
          刷新 NLM MeSH
        </button>
        <button
          ref="addButton"
          type="button"
          :disabled="props.loading"
          @click="openAddDialog"
        >
          <BaseIcon name="plus" /> 添加术语
        </button>
        <button
          type="button"
          :disabled="props.loading"
          :aria-expanded="isShowingAll"
          @click="isShowingAll = !isShowingAll"
        >
          {{ isShowingAll ? "收起" : "查看全部" }}
        </button>
      </div>
    </header>

    <div class="terms-mesh-grid">
      <section
        class="term-area"
        aria-label="检索术语"
      >
        <ul
          v-if="groups.length"
          class="concept-groups"
        >
          <li
            v-for="group in visibleGroups"
            :key="group.key"
            class="concept-group"
            :class="`concept-${group.key}`"
          >
            <div class="group-label">
              <strong>{{ group.label }}</strong>
              <span>{{ group.totalCount }} 个术语</span>
              <small
                v-if="group.originalGroup"
                class="original-group"
              >{{ group.originalGroup }}</small>
            </div>
            <div class="group-content">
              <div class="chips">
                <span
                  v-for="term in group.terms"
                  :key="term.id"
                  class="term-chip"
                  :title="term.text"
                >
                  {{ term.text }}
                </span>
              </div>
              <div class="term-meta">
                <span
                  :class="[
                    'mesh-group-status',
                    group.meshStatus
                      ? `status-${group.meshStatus}`
                      : 'status-not-queried',
                  ]"
                >{{ groupMeshStatusLabel(group.meshStatus) }}</span>
                <span>{{ sourceLabel(group.terms[0].source) }}</span>
                <span>{{
                  relationLabel(group.terms[0].relation_type, group.relation)
                }}</span>
              </div>
            </div>
            <details class="term-menu">
              <summary :aria-label="`${group.label} 操作`">
                <BaseIcon name="more" />
              </summary>
              <div class="menu-content">
                <button
                  type="button"
                  :disabled="props.loading"
                  @click="
                    emit('lock', group.terms[0].id, !group.terms[0].is_locked)
                  "
                >
                  {{ group.terms[0].is_locked ? "解锁首项" : "锁定首项" }}
                </button>
                <button
                  type="button"
                  :disabled="props.loading"
                  @click="emit('remove', group.terms[0].id)"
                >
                  删除首项
                </button>
              </div>
            </details>
          </li>
        </ul>
        <p
          v-else
          class="empty"
        >
          暂无术语。请返回上一步重新生成策略。
        </p>
        <div
          v-if="firstWarning"
          class="warning"
          role="status"
        >
          <BaseIcon name="alert" />
          <span>{{ warningTerms.length }} 个术语有提醒：{{ firstWarning.message }}</span>
          <button
            type="button"
            @click="isWarningExpanded = !isWarningExpanded"
          >
            {{ isWarningExpanded ? "收起影响" : "查看影响" }}
          </button>
          <button
            type="button"
            @click="isShowingAll = true"
          >
            处理
          </button>
        </div>
        <ul
          v-if="isWarningExpanded"
          class="warning-detail"
          role="status"
        >
          <li
            v-for="term in warningTerms"
            :key="term.id"
          >
            {{ term.text }}：{{ term.warning?.message }}
          </li>
        </ul>
      </section>

      <section
        class="mesh-area"
        aria-label="NLM MeSH 验证状态"
      >
        <h3>NLM MeSH（{{ props.meshTerms.length }} 个）</h3>
        <ul
          v-if="props.meshTerms.length"
          class="mesh-list"
        >
          <li
            v-for="term in visibleMeshTerms"
            :key="term.id"
          >
            <strong>{{ term.descriptor }}</strong>
            <span
              :class="['mesh-status', `status-${term.verification_status}`]"
            >{{ meshStatusLabel(term.verification_status) }}</span>
            <BaseIcon
              v-if="term.is_locked"
              name="lock"
              class="lock-icon"
            />
          </li>
        </ul>
        <p
          v-else
          class="empty"
        >
          尚未获得 MeSH 映射。
        </p>
        <button
          v-if="props.meshTerms.length > 5"
          type="button"
          class="show-mesh"
          :disabled="props.loading"
          @click="isShowingAll = !isShowingAll"
        >
          {{
            isShowingAll
              ? "收起 MeSH"
              : `查看全部 ${props.meshTerms.length} 个 MeSH`
          }}
          →
        </button>
      </section>
    </div>

    <dialog
      ref="addDialog"
      class="add-dialog"
      aria-labelledby="strategy-add-title"
      @close="addButton?.focus()"
    >
      <form
        method="dialog"
        @submit.prevent="addTerm"
      >
        <label
          id="strategy-add-title"
          for="strategy-new-term"
        >添加检索术语</label>
        <input
          id="strategy-new-term"
          v-model="newTerm"
          autofocus
          :disabled="props.loading"
          maxlength="300"
          placeholder="输入术语"
        >
        <div class="dialog-actions">
          <button
            type="button"
            @click="closeAddDialog"
          >
            取消
          </button>
          <button
            type="submit"
            :disabled="props.loading || !newTerm.trim()"
          >
            添加
          </button>
        </div>
      </form>
    </dialog>
  </section>
</template>

<style scoped>
.terms-mesh-section {
  box-sizing: border-box;
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 12px;
  min-width: 0;
  padding: 14px 20px;
  border: 1px solid #dbe5f2;
  border-radius: 12px;
  background: linear-gradient(135deg, #ffffff 0%, #fbfdff 100%);
  box-shadow: 0 10px 28px rgb(32 73 125 / 7%);
  overflow: visible;
}
.section-heading,
.heading-actions,
.title-row,
.statistics,
.warning,
.mesh-list li {
  display: flex;
  align-items: center;
}
.section-heading {
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 16px;
}
.title-row {
  gap: 7px;
}
.section-icon {
  box-sizing: content-box;
  width: 15px;
  height: 15px;
  padding: 3px;
  border-radius: 3px;
  background: #0b66f6;
  color: #fff;
}
.title-row h2,
.mesh-area h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 16px;
  line-height: 22px;
}
.info-icon {
  width: 15px;
  height: 15px;
  color: var(--text-muted);
}
.statistics {
  flex-wrap: wrap;
  gap: 18px;
  margin: 7px 0 0;
  color: var(--text-secondary);
  font-size: 13px;
}
.coverage-notice {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 5px 7px;
  margin: 9px 0 0;
  color: #925b12;
  font-size: 12px;
  line-height: 1.5;
}
.coverage-notice .icon {
  flex: 0 0 auto;
  width: 14px;
  height: 14px;
  margin-top: 2px;
}
.coverage-notice strong { font-weight: 700; }
.coverage-notice span { min-width: min(100%, 260px); color: var(--text-secondary); }
.statistics span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.statistics .icon {
  width: 14px;
  height: 14px;
}
.heading-actions {
  flex-wrap: wrap;
  gap: 10px;
}
.heading-actions button,
.show-mesh,
.warning button,
.dialog-actions button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid var(--border-strong);
  border-radius: 7px;
  background: var(--surface);
  color: var(--color-primary);
  font: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}
.heading-actions .icon {
  width: 14px;
  height: 14px;
}
.terms-mesh-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.07fr) minmax(0, 0.93fr);
  gap: 10px;
  min-height: 0;
}
.term-area {
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.terms-mesh-section.has-multiple-concepts {
  min-height: 376px;
}
.mesh-area {
  min-width: 0;
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: #fcfdff;
}
.concept-groups,
.mesh-list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.concept-groups {
  display: grid;
  align-content: start;
  flex: 1;
  gap: 0;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  overflow: visible;
}
.concept-group {
  display: grid;
  grid-template-columns: 76px minmax(0, 1fr) 26px;
  gap: 10px;
  min-height: 82px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle);
  background: #fff;
}
.concept-group:last-child {
  border-bottom: 0;
}
.group-label {
  padding: 6px 0;
  border-right: 1px solid #edf1f8;
  text-align: center;
}
.group-label strong {
  display: block;
  color: var(--color-primary);
  font-size: 12px;
  width: fit-content;
  margin: 0 auto;
  padding: 2px 5px;
  border-radius: 5px;
  background: #edf3ff;
}
.concept-intervention .group-label strong { background: #eaf9f3; color: #079d79; }
.concept-outcome .group-label strong { background: #f1edff; color: #6545bc; }
.group-label span {
  display: block;
  margin-top: 6px;
  color: var(--text-secondary);
  font-size: 11px;
}
.group-content {
  display: grid;
  align-content: center;
  gap: 8px;
  min-width: 0;
}
.chips {
  flex-wrap: wrap;
  display: flex;
  gap: 7px;
  min-width: 0;
  overflow: hidden;
}
.term-chip {
  min-width: 0;
  max-width: 100%;
  overflow-wrap: anywhere;
  padding: 4px 10px;
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  background: var(--surface-muted);
  color: var(--text-primary);
  font-size: 12px;
  line-height: 16px;
  white-space: normal;
}
.term-meta {
  flex-wrap: wrap;
  display: flex;
  gap: 7px;
  align-items: center;
  min-width: 0;
}
.term-meta span {
  padding: 3px 7px;
  border-radius: 5px;
  background: var(--surface-muted);
  color: var(--text-muted);
  font-size: 11px;
  overflow-wrap: anywhere;
}
.term-meta .mesh-verified {
  background: var(--color-success-soft);
  color: var(--color-success);
}
.term-menu {
  position: relative;
  align-self: start;
  justify-self: end;
}
.term-menu summary {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  color: var(--text-muted);
  cursor: pointer;
  list-style: none;
}
.term-menu summary::-webkit-details-marker {
  display: none;
}
.term-menu summary .icon {
  width: 17px;
  height: 17px;
}
.menu-content {
  position: absolute;
  right: 0;
  z-index: 4;
  display: grid;
  gap: 4px;
  min-width: 94px;
  padding: 6px;
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  background: var(--surface);
  box-shadow: var(--shadow-md);
}
.menu-content button {
  border: 0;
  background: transparent;
  color: var(--text-secondary);
  font: inherit;
  font-size: 12px;
  text-align: left;
  cursor: pointer;
}
.warning {
  gap: 8px;
  margin-top: 8px;
  padding: 9px 12px;
  border: 1px solid var(--color-warning);
  border-radius: 8px;
  background: var(--color-warning-soft);
  color: var(--color-warning);
  font-size: 12px;
}
.warning .icon {
  width: 16px;
  height: 16px;
}
.warning span {
  flex: 1;
}
.warning button {
  min-height: 28px;
  padding: 0 8px;
  border-color: transparent;
  background: transparent;
  color: var(--color-primary);
  font-size: 12px;
}
.warning button:last-child {
  border-color: var(--border-strong);
  background: var(--surface);
}
.mesh-area h3 {
  margin: 8px 0 9px;
}
.mesh-list {
  display: grid;
  border-top: 1px solid var(--border-subtle);
}
.mesh-list li {
  min-height: 37px;
  gap: 8px;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 13px;
}
.mesh-list strong {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: normal;
  overflow-wrap: anywhere;
  font-weight: 500;
}
.mesh-status {
  flex-shrink: 0;
  padding: 3px 7px;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 700;
}
.status-verified {
  background: var(--color-success-soft);
  color: var(--color-success);
}
.status-not_found,
.status-unavailable {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}
.status-stale {
  color: var(--color-danger);
}
.lock-icon {
  width: 16px;
  height: 16px;
  color: var(--text-secondary);
}
.show-mesh {
  min-height: auto;
  margin-top: 12px;
  padding: 0;
  border: 0;
  background: transparent;
}
.empty {
  margin: 14px 0;
  color: var(--text-muted);
  font-size: 13px;
}
.add-dialog {
  width: min(360px, calc(100vw - 32px));
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  box-shadow: var(--shadow-md);
}
.add-dialog form {
  display: grid;
  gap: 12px;
}
.add-dialog label {
  font-weight: 700;
}
.add-dialog input {
  min-height: 36px;
  border: 1px solid var(--border-strong);
  border-radius: 7px;
  padding: 0 9px;
  font: inherit;
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.add-dialog::backdrop {
  background: color-mix(in srgb, var(--text-primary) 24%, transparent);
}
button:disabled {
  opacity: 0.55;
  cursor: wait;
}
button:focus-visible,
input:focus-visible,
summary:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
@media (max-width: 1120px) {
  .terms-mesh-section {
    height: auto;
    min-height: 0;
  }
  .terms-mesh-grid {
    grid-template-columns: 1fr;
  }
  .mesh-area {
    padding: 12px 14px;
  }
}
@media (max-width: 640px) {
  .section-heading {
    align-items: stretch;
    flex-direction: column;
  }
  .heading-actions {
    flex-wrap: wrap;
  }
  .statistics {
    flex-wrap: wrap;
  }
  .concept-group {
    grid-template-columns: 70px minmax(0, 1fr) 24px;
  }
  .term-meta {
    flex-wrap: wrap;
  }
  .warning {
    align-items: flex-start;
    flex-wrap: wrap;
  }
  .warning span {
    min-width: calc(100% - 24px);
  }
}
.original-group { display: block; padding: 4px; overflow-wrap: anywhere; color: var(--text-muted); font-size: 10px; }
.warning-detail { font-size: 12px; color: var(--color-warning); overflow-wrap: anywhere; }
.warning { flex-wrap: wrap; }
.warning span { min-width: 0; overflow-wrap: anywhere; }
.heading-copy { min-width: 0; }
.term-meta .mesh-group-status.status-verified {
  background: var(--color-success-soft);
  color: var(--color-success);
}
.term-meta .mesh-group-status.status-not_found,
.term-meta .mesh-group-status.status-unavailable {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}
.term-meta .mesh-group-status.status-stale {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}
.term-meta .mesh-group-status.status-not-queried {
  background: var(--surface-muted);
  color: var(--text-muted);
}
</style>
