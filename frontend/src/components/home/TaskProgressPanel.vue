<script setup lang="ts">
import { computed, onMounted, shallowRef } from "vue";
import { documentsApi, type DocumentRecord } from "../../api/documents";

const loading = shallowRef(false);
const error = shallowRef("");
const items = shallowRef<DocumentRecord[]>([]);

async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    items.value = (await documentsApi.list({ parseStatus: "", indexStatus: "" }, 0, 100)).items;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法读取任务状态";
  } finally {
    loading.value = false;
  }
}
onMounted(load);

interface TaskView { id: string; title: string; subtitle: string; state: string; stateClass: string; percent: number; time: string; }
function toView(item: DocumentRecord): TaskView {
  const base = item.file_path.split(/[\\/]/).pop() ?? item.file_path;
  const running = item.parse_status === "parsing" || item.index_status === "indexing";
  const failed = item.parse_status === "failed" || item.index_status === "failed";
  const done = item.parse_status === "succeeded" && item.index_status === "succeeded";
  const state = failed ? "失败" : running ? "处理中" : done ? "已完成" : "排队中";
  const stateClass = failed ? "failed" : running ? "running" : done ? "done" : "queued";
  const percent = failed ? 0 : done ? 100 : running ? 60 : 15;
  const time = item.finished_at ?? item.started_at ?? item.modified_time;
  return { id: `doc-${item.id}`, title: base, subtitle: `文档解析 / 索引`, state, stateClass, percent, time };
}
const tasks = computed(() => items.value.slice(0, 4).map(toView));
</script>
<template>
  <section class="task-panel" aria-label="任务中心">
    <div class="panel-head">
      <h2>任务中心</h2>
      <RouterLink to="/tasks">全部 →</RouterLink>
    </div>
    <p class="source-note">仅展示已有接口返回的文档解析与索引状态 · LIVE</p>
    <p v-if="loading" class="hint">正在读取真实状态…</p>
    <p v-else-if="error" class="hint error">{{ error }}</p>
    <p v-else-if="!tasks.length" class="hint">暂无运行中的任务。</p>
    <ul v-else class="task-list">
      <li v-for="task in tasks" :key="task.id" class="task">
        <div class="task-line"><span class="task-title">{{ task.title }}</span><span class="task-state" :class="task.stateClass">{{ task.state }}</span></div>
        <p class="task-sub">{{ task.subtitle }} · {{ task.time }}</p>
        <div class="progress"><i :class="task.stateClass" :style="{ width: `${task.percent}%` }"></i></div>
      </li>
    </ul>
  </section>
</template>
<style scoped>
.task-panel{min-width:0}.panel-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:.4rem}.panel-head h2{margin:0;font-size:1rem;color:var(--text-primary)}.panel-head a{color:var(--text-muted);font-size:.8rem;text-decoration:none}.panel-head a:hover{color:var(--color-primary)}.source-note{margin:0 0 .6rem;color:var(--text-faint);font-size:.72rem}.hint{padding:.85rem .95rem;color:var(--text-muted);font-size:.84rem;background:var(--surface);border:1px dashed var(--border-subtle);border-radius:10px}.hint.error{color:var(--color-danger)}.task-list{display:grid;gap:.55rem;margin:0;padding:0;list-style:none}.task{padding:.7rem .8rem;background:var(--surface);border:1px solid var(--border-subtle);border-radius:10px}.task-line{display:flex;align-items:center;justify-content:space-between;gap:.6rem}.task-title{font-size:.85rem;font-weight:700;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.task-state{flex-shrink:0;padding:.15rem .5rem;border-radius:99px;font-size:.72rem;font-weight:800}.task-state.running{background:var(--color-primary-soft);color:var(--color-primary)}.task-state.done{background:var(--color-success-soft);color:var(--color-success)}.task-state.failed{background:var(--color-danger-soft);color:var(--color-danger)}.task-state.queued{background:var(--color-warning-soft);color:var(--color-warning)}.task-sub{margin:.3rem 0 .45rem;color:var(--text-faint);font-size:.74rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.progress{height:4px;border-radius:99px;background:var(--surface-muted);overflow:hidden}.progress i{display:block;height:100%;border-radius:99px;transition:width .15s}.progress i.running{background:var(--color-primary)}.progress i.done{background:var(--color-success)}.progress i.failed{background:var(--color-danger)}.progress i.queued{background:var(--color-warning)}
</style>
