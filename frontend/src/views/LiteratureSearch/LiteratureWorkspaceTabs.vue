<script setup lang="ts">
// 文献检索工作空间内的局部二级导航：检索中心 / 结果展示 / 历史记录 / 推荐阅读。
// 只作用于本工作空间，不进入左侧全局导航；结果页只链接至真实已有的检索结果。
import { onMounted, ref } from "vue";
import { literatureSearchApi } from "../../api/literatureSearch";

const props = defineProps<{ activeTab: "center" | "results" | "history" | "recommendations" }>();
const emit = defineEmits<{
  select: [tab: "center" | "results" | "history" | "recommendations"];
  "select-result": [result: { resultId: number; taskId: number }];
}>();
const latestResult = ref<{ resultId: number; taskId: number } | null>(null);

const tabs = [
  { key: "center", label: "检索中心" },
  { key: "results", label: "结果展示", requiresResult: true },
  { key: "history", label: "历史记录" },
  { key: "recommendations", label: "推荐阅读" },
] as const;

onMounted(async () => {
  try {
    const page = await literatureSearchApi.listTasks(0, 50);
    const task = page.items.find((item) => item.status === "succeeded" && item.latest_result_id !== null);
    if (task?.latest_result_id !== null && task?.latest_result_id !== undefined) {
      latestResult.value = { resultId: task.latest_result_id, taskId: task.id };
    }
  } catch {
    // 保持不可用状态：不能在接口失败时伪造一个结果页地址。
    latestResult.value = null;
  }
});

function openTab(tab: (typeof tabs)[number]): void {
  // 在固定的文献检索工作区内切换内容；不跳转到另一张页面。
  if (tab.key === "results") {
    if (latestResult.value) {
      emit("select-result", latestResult.value);
      emit("select", "results");
    }
    return;
  }
  emit("select", tab.key);
}
</script>

<template>
  <nav class="workspace-tabs" aria-label="文献检索工作空间导航">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      type="button"
      class="workspace-tab"
      :class="{ active: props.activeTab === tab.key, disabled: tab.key === 'results' && !latestResult && props.activeTab !== 'results' }"
      :aria-current="props.activeTab === tab.key ? 'page' : undefined"
      :aria-disabled="tab.key === 'results' && !latestResult && props.activeTab !== 'results' ? 'true' : undefined"
      :title="tab.key === 'results' && !latestResult && props.activeTab !== 'results' ? '完成一次检索后可查看结果展示' : undefined"
      @click="openTab(tab)"
    >
      {{ tab.label }}
    </button>
  </nav>
</template>

<style scoped>
.workspace-tabs {
  display: flex;
  gap: 0.25rem;
  padding: 0.35rem 0;
  border-bottom: 1px solid var(--border-subtle, #e2e8f0);
}
.workspace-tab {
  padding: 0.4rem 0.9rem;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary, #475569);
  font: inherit;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
}
.workspace-tab:hover {
  background: var(--color-primary-soft, #eff6ff);
  color: var(--color-primary, #2563eb);
}
.workspace-tab:focus-visible {
  outline: 2px solid var(--color-primary, #2563eb);
  outline-offset: 2px;
}
.workspace-tab.active {
  background: var(--color-primary-soft, #eff6ff);
  color: var(--color-primary, #2563eb);
  font-weight: 600;
}
.workspace-tab.disabled {
  color: var(--text-faint, #94a3b8);
  cursor: not-allowed;
}
.workspace-tab.disabled:hover {
  background: transparent;
  color: var(--text-faint, #94a3b8);
}
</style>
