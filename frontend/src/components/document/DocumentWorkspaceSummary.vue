<script setup lang="ts">
import { computed } from "vue";

import type { KnowledgeSourceStats } from "../../api/knowledgeSources";

const props = defineProps<{
  sourceName: string | null;
  total: number;
  stats: KnowledgeSourceStats | null;
}>();

const metrics = computed(() => [
  { key: "total", label: "文件总数", value: props.total, available: true },
  { key: "parsed", label: "已解析", value: props.stats?.parsed ?? null, available: Boolean(props.stats) },
  { key: "indexed", label: "已索引", value: props.stats?.indexed ?? null, available: Boolean(props.stats) },
  { key: "pending", label: "待处理", value: props.stats?.pending ?? null, available: Boolean(props.stats) },
  { key: "failed", label: "异常", value: props.stats?.failed ?? null, available: Boolean(props.stats) },
]);
</script>

<template>
  <header class="workspace-summary">
    <div class="summary-title">
      <p class="scope-name">{{ props.sourceName ?? "全部文档" }}</p>
    </div>

    <dl class="metrics" aria-label="当前范围统计">
      <div
        v-for="metric in metrics"
        :key="metric.key"
        class="metric"
        :class="`metric-${metric.key}`"
      >
        <dt>{{ metric.label }}</dt>
        <dd
          :class="{ 'metric-value--unavailable': !metric.available }"
          :title="metric.available ? undefined : '全部知识库暂不提供聚合处理统计'"
        >
          {{ metric.available ? metric.value : "—" }}
        </dd>
      </div>
    </dl>
  </header>
</template>

<style scoped>
.workspace-summary {
  box-sizing: border-box;
  display: grid;
  grid-template-columns: minmax(150px, 0.3fr) minmax(0, 1fr);
  align-items: center;
  gap: 20px;
  min-height: 76px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-subtle);
}

.summary-title p {
  margin: 0;
}

.scope-name {
  color: var(--ink-900, #10213d);
  font-size: 1rem;
  font-weight: 700;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  margin: 0;
  border-left: 1px solid var(--border-subtle);
}

.metric {
  display: grid;
  gap: 2px;
  min-width: 0;
  padding: 3px 12px;
  border-left: 1px solid var(--border-subtle);
}

.metric:first-child {
  border-left: 0;
}

.metric dt {
  color: var(--text-muted);
  font-size: 0.75rem;
}

.metric dd {
  margin: 0;
  color: var(--ink-900, #10213d);
  font-size: 1rem;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}

.metric-parsed dd,
.metric-indexed dd {
  color: var(--color-success);
}

.metric-pending dd {
  color: var(--color-primary);
}

.metric-failed dd {
  color: var(--color-danger);
}

.metric-value--unavailable {
  color: var(--text-muted) !important;
}

@media (max-width: 700px) {
  .workspace-summary {
    grid-template-columns: 1fr;
    gap: 10px;
    min-height: 0;
  }

  .metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metric:nth-child(odd) {
    border-left: 0;
    padding-left: 0;
  }

  .metric {
    border-top: 1px solid var(--border-subtle);
  }

  .metric:first-child,
  .metric:nth-child(2) {
    border-top: 0;
  }

  .metric:first-child { border-left: 0; }
}
</style>
