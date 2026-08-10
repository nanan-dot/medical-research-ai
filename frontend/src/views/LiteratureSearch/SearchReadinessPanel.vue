<script setup lang="ts">
// 检索前检查：根据真实表单状态计算完成项，不写死全部完成。
// 提供保存策略（本地草稿，不伪称已保存到后端）与执行检索（真实 createTask）。
import { computed } from "vue";

const props = defineProps<{
  topicFilled: boolean;
  picoFilled: boolean;
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
  { label: "准备开始检索", done: props.topicFilled && props.picoFilled && props.sourceSelected && props.draftReady },
]);

const allReady = computed(() => items.value.every((item) => item.done));
</script>

<template>
  <section class="readiness-panel" aria-labelledby="readiness-panel-title">
    <h2 id="readiness-panel-title" class="section-title">检索前检查</h2>
    <ul class="check-list">
      <li v-for="item in items" :key="item.label" class="check-item" :class="{ done: item.done }">
        <span class="check-mark" aria-hidden="true">{{ item.done ? "✓" : "○" }}</span>
        <span>{{ item.label }}</span>
      </li>
    </ul>
    <div class="readiness-actions">
      <button type="button" class="secondary-action" @click="emit('saveDraft')">保存为检索策略</button>
      <button
        type="button"
        class="primary-action"
        :disabled="!allReady || props.taskLoading"
        @click="emit('runSearch')"
      >
        {{ props.taskLoading ? "检索中…" : "开始检索" }}
      </button>
    </div>
    <p v-if="props.taskError" class="request-error" role="alert">{{ props.taskError }}</p>
    <p class="footnote">本页用于设计检索策略；结果与历史将在相应页面查看。</p>
  </section>
</template>

<style scoped>
.readiness-panel {
  display: grid;
  gap: 0.8rem;
  padding: 1.25rem;
  background: var(--surface, #fff);
  border: 1px solid var(--border-subtle, #e2e8f0);
  border-radius: 8px;
}
.section-title {
  margin: 0;
  color: var(--text-primary, #0f2a43);
  font-size: 1.05rem;
}
.check-list {
  display: grid;
  gap: 0.45rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.check-item {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.9rem;
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
  padding-top: 0.35rem;
}
.secondary-action {
  padding: 0.55rem 1rem;
  border: 1px solid var(--border-strong, #cbd5e1);
  border-radius: 6px;
  background: transparent;
  color: var(--text-primary, #0f2a43);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}
.primary-action {
  padding: 0.55rem 1.2rem;
  border: 0;
  border-radius: 6px;
  background: var(--color-primary, #2563eb);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
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
  font-size: 0.8rem;
  color: var(--text-muted, #64748b);
}
@media (max-width: 640px) {
  .readiness-actions {
    flex-wrap: wrap;
  }
}
</style>
