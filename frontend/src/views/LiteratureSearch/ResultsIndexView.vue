<script setup lang="ts">
import { onMounted, shallowRef } from "vue";
import { useRouter } from "vue-router";

import { literatureSearchApi } from "../../api/literatureSearch";

const router = useRouter();
const isLoading = shallowRef(true);
const requestError = shallowRef("");

async function restoreLatestResult(): Promise<void> {
  isLoading.value = true;
  requestError.value = "";
  try {
    const history = await literatureSearchApi.listHistory(0, 100);
    const latestWithResults = history.items.find((entry) => entry.latest_result_id !== null);
    if (latestWithResults?.latest_result_id !== null && latestWithResults?.latest_result_id !== undefined) {
      await router.replace({
        path: `/literature-search/results/${latestWithResults.latest_result_id}`,
        query: { task: String(latestWithResults.id), from: "history" },
      });
    }
  } catch (cause) {
    requestError.value = cause instanceof Error ? cause.message : "暂时无法读取检索历史";
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => { void restoreLatestResult(); });
</script>

<template>
  <main
    class="results-index"
    aria-labelledby="results-index-title"
  >
    <h1 id="results-index-title">检索结果</h1>
    <p v-if="isLoading" role="status">正在恢复最近一次检索结果…</p>
    <template v-else>
      <p v-if="requestError" class="request-error" role="alert">{{ requestError }}</p>
      <p>尚未找到可恢复的检索结果。请从历史记录打开真实检索快照，或先创建新的检索策略。</p>
    </template>
    <div v-if="!isLoading" class="actions">
      <RouterLink to="/literature-search/history">打开检索历史</RouterLink>
      <RouterLink to="/literature-search">前往检索中心</RouterLink>
    </div>
  </main>
</template>

<style scoped>
.results-index {
  display: grid;
  gap: 16px;
  max-width: 760px;
  margin: 0 auto;
  padding: 48px 32px;
  color: var(--text-primary);
}

.results-index h1,
.results-index p {
  margin: 0;
}

.request-error {
  color: var(--color-danger, #b42318) !important;
}

.results-index p {
  color: var(--text-muted);
  line-height: 1.6;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.actions a {
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  padding: 0 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  color: var(--color-primary);
  font-weight: 700;
  text-decoration: none;
}

.actions a:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
</style>
