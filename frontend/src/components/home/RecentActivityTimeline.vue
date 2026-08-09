<script setup lang="ts">
// 最近活动：从真实后端读取最近的研究任务并按时间倒序展示。
// 无记录时显示空态，不伪造任何活动条目。
import { onMounted, shallowRef } from "vue";
import { literatureSearchApi } from "../../api/literatureSearch";

interface ActivityItem {
  id: string;
  kind: string;
  text: string;
  time: string;
}

const loading = shallowRef(true);
const error = shallowRef("");
const activities = shallowRef<ActivityItem[]>([]);

const KIND_LABEL: Record<string, string> = {
  succeeded: "检索文献",
  running: "检索文献",
  pending: "检索文献",
  failed: "检索文献",
};

function formatTime(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const sameDay = date.toDateString() === now.toDateString();
  const time = date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false });
  return sameDay ? `今天 ${time}` : date.toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" }) + ` ${time}`;
}

onMounted(async () => {
  try {
    const page = await literatureSearchApi.listTasks(0, 10);
    activities.value = [...page.items]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 4)
      .map((task) => ({
        id: String(task.id),
        kind: KIND_LABEL[task.status] ?? "任务",
        text: task.original_query,
        time: formatTime(task.created_at),
      }));
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法读取最近活动";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section class="activity-panel" aria-label="最近活动">
    <div class="panel-head">
      <h2 class="panel-title">最近活动</h2>
    </div>

    <p v-if="loading" class="hint">正在读取最近活动…</p>
    <p v-else-if="error" class="hint error">{{ error }}</p>
    <p v-else-if="!activities.length" class="hint empty">暂无活动记录。</p>

    <ol v-else class="timeline">
      <li v-for="activity in activities" :key="activity.id" class="timeline-item">
        <!-- 时间线节点 + 细窄证据轨道 -->
        <span class="track" aria-hidden="true"></span>
        <div class="item-body">
          <div class="item-line">
            <span class="kind">{{ activity.kind }}</span>
            <time class="time">{{ activity.time }}</time>
          </div>
          <p class="text">{{ activity.text }}</p>
        </div>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.activity-panel {
  min-width: 0;
}
.panel-head {
  margin-bottom: 0.7rem;
}
.panel-title {
  margin: 0;
  color: var(--text-primary);
  font-size: 1rem;
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
.timeline {
  display: grid;
  gap: 0;
  margin: 0;
  padding: 0;
  list-style: none;
}
.timeline-item {
  position: relative;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.9rem;
  min-height: 46px;
}
.track {
  position: relative;
  width: 2px;
  margin-left: 5px;
  background: var(--border-subtle);
}
.track::before {
  content: "";
  position: absolute;
  top: 6px;
  left: 50%;
  transform: translateX(-50%);
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}
.timeline-item:not(:last-child) .track {
  background: linear-gradient(to bottom, var(--border-subtle) 0 92%, transparent 92% 100%);
}
.item-body {
  min-width: 0;
  padding: 0.35rem 0 0.55rem;
}
.item-line {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.8rem;
}
.kind {
  color: var(--color-primary);
  font-size: 0.8rem;
  font-weight: 800;
}
.time {
  flex-shrink: 0;
  color: var(--text-faint);
  font-size: 0.74rem;
}
.text {
  margin: 0.15rem 0 0;
  color: var(--text-primary);
  font-size: 0.84rem;
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
