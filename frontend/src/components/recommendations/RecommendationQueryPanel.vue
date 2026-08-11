<script setup lang="ts">
interface Props {
  query: string;
  candidateCount: number;
  loading: boolean;
}

defineProps<Props>();
const emit = defineEmits<{ "update:query": [value: string]; "update:candidateCount": [value: number]; submit: [] }>();
</script>

<template>
  <form class="query-panel" @submit.prevent="emit('submit')">
    <div class="panel-heading">
      <div>
        <label for="recommendation-query">研究主题</label>
        <p>仅检索 PubMed；结果、推荐理由和状态均由服务端返回。</p>
      </div>
      <span class="source-label">数据源：PubMed</span>
    </div>
    <textarea id="recommendation-query" :value="query" maxlength="1000" rows="3" placeholder="输入研究问题或主题" required @input="emit('update:query', ($event.target as HTMLTextAreaElement).value)" />
    <div class="query-controls">
      <label class="count-control" for="candidate-count">推荐数量
        <select id="candidate-count" :value="candidateCount" @change="emit('update:candidateCount', Number(($event.target as HTMLSelectElement).value))">
          <option v-for="count in [3, 5, 8, 10]" :key="count" :value="count">{{ count }} 篇</option>
        </select>
      </label>
      <button type="submit" :disabled="loading || !query.trim()">{{ loading ? "正在检索" : "生成推荐" }}</button>
    </div>
  </form>
</template>

<style scoped>
.query-panel{display:grid;gap:12px;padding:16px;border:1px solid var(--border-subtle);border-radius:8px;background:var(--surface)}.panel-heading,.query-controls{display:flex;align-items:center;justify-content:space-between;gap:12px}.panel-heading label{font-size:.9rem;font-weight:700}.panel-heading p{margin:4px 0 0;color:var(--text-muted);font-size:.78rem}.source-label{padding:4px 8px;border:1px solid var(--border-subtle);background:var(--surface-muted);color:var(--text-secondary);font:600 .72rem ui-monospace,SFMono-Regular,Consolas,monospace}.query-panel textarea,.count-control select{box-sizing:border-box;width:100%;padding:8px;border:1px solid var(--border-strong);border-radius:6px;background:var(--surface);color:var(--text-primary);font:inherit}.query-panel textarea:focus-visible,.count-control select:focus-visible,button:focus-visible{outline:2px solid var(--color-primary);outline-offset:2px}.count-control{display:flex;align-items:center;gap:8px;color:var(--text-secondary);font-size:.82rem}.count-control select{width:auto;padding:6px;font-variant-numeric:tabular-nums}button{min-height:36px;padding:8px 12px;border:0;border-radius:6px;background:var(--color-primary);color:#fff;font:700 .84rem inherit;cursor:pointer}button:disabled{opacity:.55;cursor:not-allowed}@media(max-width:640px){.panel-heading,.query-controls{align-items:stretch;flex-direction:column}.source-label{align-self:flex-start}.count-control{justify-content:space-between}.count-control select{width:7rem}button{width:100%}}
</style>
