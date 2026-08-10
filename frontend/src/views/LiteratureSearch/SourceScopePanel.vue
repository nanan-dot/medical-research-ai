<script setup lang="ts">
// 来源范围：本地表单状态选择检索数据库候选。
// 明确边界：此处是用户选择的前端状态，不声称已经访问这些数据库；
// 执行检索时使用后端 createTask 的 database 字段（当前为 pubmed 单库）。
import { reactive, watch } from "vue";

const sources = reactive({
  pubmed: true,
  embase: false,
  cochrane: false,
});

const emit = defineEmits<{ change: [selected: string[]] }>();

function selectedList(): string[] {
  const list: string[] = [];
  if (sources.pubmed) list.push("pubmed");
  if (sources.embase) list.push("embase");
  if (sources.cochrane) list.push("cochrane");
  return list;
}

watch(sources, () => emit("change", selectedList()), { deep: true });
</script>

<template>
  <section class="source-panel" aria-labelledby="source-panel-title">
    <h3 id="source-panel-title" class="panel-title">来源范围</h3>
    <div class="source-list" role="group" aria-label="检索数据库来源">
      <label class="source-option">
        <input v-model="sources.pubmed" type="checkbox" />
        <span>PubMed</span>
      </label>
      <label class="source-option">
        <input v-model="sources.embase" type="checkbox" />
        <span>Embase</span>
      </label>
      <label class="source-option">
        <input v-model="sources.cochrane" type="checkbox" />
        <span>Cochrane Library</span>
      </label>
    </div>
    <p class="source-note">覆盖医学文献与系统综述</p>
  </section>
</template>

<style scoped>
.source-panel {
  display: grid;
  gap: 0.7rem;
  padding: 1.25rem;
  background: var(--surface, #fff);
  border: 1px solid var(--border-subtle, #e2e8f0);
  border-radius: 8px;
  align-content: start;
}
.panel-title {
  margin: 0;
  color: var(--text-primary, #0f2a43);
  font-size: 1rem;
}
.source-list {
  display: grid;
  gap: 0.5rem;
}
.source-option {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.9rem;
  color: var(--text-primary, #0f2a43);
  cursor: pointer;
}
.source-option input {
  width: 1rem;
  height: 1rem;
  accent-color: var(--color-primary, #2563eb);
}
.source-option input:focus-visible {
  outline: 2px solid var(--color-primary, #2563eb);
  outline-offset: 2px;
}
.source-note {
  margin: 0;
  font-size: 0.8rem;
  color: var(--text-muted, #64748b);
}
</style>
