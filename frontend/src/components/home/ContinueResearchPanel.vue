<script setup lang="ts">
// 继续研究：从真实后端读取最近的研究任务（文献检索历史）。
// 无记录时显示空态引导，不伪造任何研究记录。
import { onMounted, shallowRef } from "vue";
import { literatureSearchApi } from "../../api/literatureSearch";

interface RecentResearch {
  id: number;
  resultId: number | null;
  title: string;
  lastAction: string;
  meta: string;
}

const loading = shallowRef(true);
const error = shallowRef("");
const items = shallowRef<RecentResearch[]>([]);

onMounted(async () => {
  try {
    const page = await literatureSearchApi.listHistory(0, 10);
    items.value = page.items.map((task) => ({
      id: task.id,
      resultId: task.latest_result_id,
      title: task.original_query,
      lastAction: task.status === "succeeded" ? `检索完成，共 ${task.result_count} 篇结果` : `当前状态：${task.status}`,
      meta: task.searched_at
        ? `最近运行：${new Date(task.searched_at).toLocaleString("zh-CN", { hour12: false })}`
        : "尚未完成检索",
    }));
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法读取研究记录";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section class="continue-panel" aria-label="继续研究">
    <div class="panel-head">
      <h2 class="panel-title">继续研究</h2>
      <RouterLink class="more" to="/literature-search/history">查看全部研究记录 →</RouterLink>
    </div>

    <p v-if="loading" class="hint">正在读取研究记录…</p>
    <p v-else-if="error" class="hint error">{{ error }}</p>
    <p v-else-if="!items.length" class="hint empty">暂无研究记录。从上方"研究起点"开始你的第一项研究。</p>

    <ul v-else class="record-list">
      <li v-for="record in items" :key="record.id" class="record">
        <!-- 证据轨道：细窄蓝线 + 端点，语义化为"该条研究有真实检索产出" -->
        <span class="evidence-track" aria-hidden="true"></span>
        <div class="record-body">
          <h3 class="record-title">{{ record.title }}</h3>
          <p class="record-action">{{ record.lastAction }}</p>
          <p class="record-meta">{{ record.meta }}</p>
          <RouterLink v-if="record.resultId" class="link-btn" :to="`/literature-search/results/${record.resultId}?task=${record.id}`">查看结果</RouterLink>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.continue-panel {
  min-width: 0;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
  margin-bottom: 0.7rem;
}
.panel-title {
  margin: 0;
  color: var(--text-primary);
  font-size: 1rem;
}
.more {
  color: var(--text-muted);
  font-size: 0.78rem;
  text-decoration: none;
}
.more:hover,
.more:focus-visible {
  color: var(--color-primary);
}
.hint {
  margin: 0;
  padding: 1rem;
  color: var(--text-muted);
  font-size: 0.84rem;
  background: var(--surface);
  border: 1px dashed var(--border-subtle);
  border-radius: 10px;
}
.hint.error {
  color: var(--color-danger);
}
.hint.empty {
  color: var(--text-faint);
}
.record-list {
  display: grid;
  gap: 0.7rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.record {
  position: relative;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.85rem;
  padding: 0.9rem 0.95rem 0.95rem 0;
  background: var(--surface);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
}
.evidence-track {
  position: relative;
  width: 3px;
  margin: 0.5rem 0 0.5rem 0.9rem;
  border-radius: 99px;
  background: linear-gradient(to bottom, var(--color-primary) 0 78%, transparent 78% 100%);
}
.evidence-track::before {
  content: "";
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}
.record-body {
  min-width: 0;
}
.record-title {
  margin: 0 0 0.3rem;
  color: var(--text-primary);
  font-size: 0.88rem;
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.record-action {
  margin: 0 0 0.25rem;
  color: var(--text-muted);
  font-size: 0.78rem;
}
.record-meta {
  margin: 0 0 0.55rem;
  color: var(--text-faint);
  font-size: 0.74rem;
}
.link-btn {
  display: inline-block;
  padding: 0.32rem 0.7rem;
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  background: var(--surface);
  color: var(--color-primary);
  font-size: 0.78rem;
  font-weight: 700;
  text-decoration: none;
  transition: background-color 0.15s, border-color 0.15s;
}
.link-btn:hover,
.link-btn:focus-visible {
  background: var(--nav-active-bg);
  border-color: var(--color-primary);
  outline: none;
}
</style>
