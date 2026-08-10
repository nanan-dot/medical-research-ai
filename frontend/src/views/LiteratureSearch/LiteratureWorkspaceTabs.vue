<script setup lang="ts">
// 文献检索工作空间内的局部二级导航：检索中心 / 结果 / 历史 / 推荐阅读。
// 只作用于本工作空间，不进入左侧全局导航；结果页仅在存在有效结果时可用。
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

const tabs = [
  { key: "center", label: "检索中心", to: "/literature-search", exact: true },
  // 结果：无最近检索结果时禁用（跳转到检索中心引导先开始检索）
  { key: "results", label: "结果", to: "", exact: false, requiresResult: true },
  { key: "history", label: "历史", to: "/literature-search/history", exact: false },
  { key: "recommendations", label: "推荐阅读", to: "/recommendations", exact: false },
] as const;

function isActive(tab: (typeof tabs)[number]): boolean {
  if (tab.key === "center") return route.path === "/literature-search";
  if (tab.key === "history") return route.path.startsWith("/literature-search/history");
  if (tab.key === "recommendations") return route.path.startsWith("/recommendations");
  return route.path.startsWith("/literature-search/results");
}

function openTab(tab: (typeof tabs)[number]): void {
  // 结果页需要有效结果；没有时安全引导回检索中心，不伪造结果入口。
  if (tab.key === "results") {
    router.push("/literature-search");
    return;
  }
  if (tab.to) router.push(tab.to);
}
</script>

<template>
  <nav class="workspace-tabs" aria-label="文献检索工作空间导航">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      type="button"
      class="workspace-tab"
      :class="{ active: isActive(tab) }"
      :aria-current="isActive(tab) ? 'page' : undefined"
      :aria-label="tab.key === 'results' ? '结果（需先完成一次检索）' : tab.label"
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
</style>
