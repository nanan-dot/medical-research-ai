<script setup lang="ts">
// 检索前检查：根据真实表单状态计算完成项，不写死全部完成。
// 保存策略通过父组件的真实后端草稿接口；执行检索创建真实任务与结果快照。
import { computed } from "vue";

const props = defineProps<{
  topicFilled: boolean;
  sourceSelected: boolean;
  draftReady: boolean;
  taskLoading: boolean;
  taskError: string | null;
  hasCandidate: boolean;
}>();

const emit = defineEmits<{
  saveDraft: [];
  runSearch: [];
}>();

const items = computed(() => [
  { label: "研究问题已明确", done: props.topicFilled },
  { label: "关键词已扩展", done: props.hasCandidate && props.draftReady },
  { label: "来源范围已选择", done: props.sourceSelected },
  { label: "准备开始检索", done: props.topicFilled && props.sourceSelected && props.draftReady },
]);

const allReady = computed(() => items.value.every((item) => item.done));
</script>

<template>
  <section
    class="readiness-panel"
    aria-labelledby="readiness-panel-title"
  >
    <div class="readiness-summary">
      <h2
        id="readiness-panel-title"
        class="sr-only"
      >
        检索前检查
      </h2>
      <ul class="check-list">
        <li
          v-for="item in items"
          :key="item.label"
          class="check-item"
          :class="{ done: item.done }"
        >
          <span
            class="check-mark"
            aria-hidden="true"
          >{{ item.done ? "✓" : "○" }}</span>
          <span>{{ item.label }}</span>
        </li>
      </ul>
    </div>
    <div class="readiness-actions">
      <button
        type="button"
        class="secondary-action"
        @click="emit('saveDraft')"
      >
        保存草稿
      </button>
      <button
        type="button"
        class="primary-action"
        :disabled="!allReady || props.taskLoading"
        @click="emit('runSearch')"
      >
        {{ props.taskLoading ? "检索中…" : "开始检索" }}
      </button>
    </div>
    <p
      v-if="props.taskError"
      class="request-error"
      role="alert"
    >
      {{ props.taskError }}
    </p>
    <p class="footnote">策略草稿会保存到服务端；执行后才会产生真实检索结果。</p>
  </section>
</template>

<style scoped>
.readiness-panel {
  display: flex;
  gap: .75rem 1rem;
  align-items: center;
  flex-wrap: wrap;
  padding: .85rem 1rem;
  background: var(--surface-muted, #f8fafc);
  border: 0;
  border-top: 1px solid var(--border-subtle, #e2e8f0);
  border-radius: 0;
}
.readiness-summary { display: grid; flex: 1 1 22rem; min-width: 0; }
.check-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: .35rem .75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.check-item {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-size: .78rem;
  color: var(--text-muted, #64748b);
}
.check-item.done {
  color: var(--text-primary, #0f2a43);
}
.check-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.1rem;
  height: 1.1rem;
  border: 1px solid var(--border-strong, #cbd5e1);
  border-radius: 50%;
  font-size: 0.7rem;
}
.check-item.done .check-mark {
  background: #16a34a;
  border-color: #16a34a;
  color: #fff;
}
.readiness-actions {
  display: flex;
  gap: 0.6rem;
  align-items: center;
  justify-content: flex-end;
  padding-top: 0;
}
.secondary-action {
  padding: .48rem .7rem;
  border: 1px solid var(--border-strong, #cbd5e1);
  border-radius: 6px;
  background: transparent;
  color: var(--text-primary, #0f2a43);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.primary-action {
  padding: .48rem .8rem;
  border: 0;
  border-radius: 6px;
  background: var(--color-primary, #2563eb);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.primary-action:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.request-error {
  margin: 0;
  padding: 0.6rem 0.8rem;
  color: var(--color-danger, #dc2626);
  background: var(--color-danger-soft, #fef2f2);
  border-radius: 6px;
  font-size: 0.85rem;
}
.footnote {
  margin: 0;
  flex-basis: 100%;
  font-size: .75rem;
  color: var(--text-muted, #64748b);
}
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
@media (max-width: 640px) {
  .readiness-actions {
    flex-wrap: wrap;
  }
  .readiness-panel { grid-template-columns: 1fr; }
  .check-list { grid-template-columns: 1fr; }
  .readiness-actions { justify-content: flex-start; }
}
</style>
