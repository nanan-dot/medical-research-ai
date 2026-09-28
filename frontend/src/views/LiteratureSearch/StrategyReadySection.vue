<script setup lang="ts">
import { computed } from "vue";
import type { SearchStrategyDraft, StrategyValidation } from "../../types/searchStrategy";
import { strategyReadiness } from "./strategyReadiness";

const props = defineProps<{
  strategy: SearchStrategyDraft;
  validation: StrategyValidation | null;
  queryText?: string;
  countAvailable: boolean;
  actionError: string | null;
}>();
const readiness = computed(() => strategyReadiness(props.strategy, props.queryText ?? props.strategy.query_text, props.validation));
</script>

<template>
  <section
    class="strategy-ready"
    :class="`state-${readiness.state}`"
    aria-labelledby="strategy-ready-title"
  >
    <h2
      id="strategy-ready-title"
      aria-live="polite"
    >
      {{ readiness.title }}
    </h2>
    <ul class="readiness-checks">
      <li
        v-for="check in readiness.checks"
        :key="check.label"
        :class="{ passed: check.passed }"
      >
        <span aria-hidden="true">{{ check.passed ? "✓" : "!" }}</span>{{ check.label }}
      </li>
    </ul>
    <p class="helper">{{ readiness.helper }}{{ props.countAvailable ? " 已获取当前匹配数量。" : "" }}</p>
    <p
      v-if="props.actionError"
      class="error"
      role="alert"
    >
      {{ props.actionError }}
    </p>
  </section>
</template>

<style scoped>
.strategy-ready { min-width: 0; display: grid; align-content: center; gap: 5px; padding: 10px 20px; border: 1px solid var(--border-subtle); border-radius: 12px; background: #f8faff; }
.strategy-ready.state-ready { background: #f5fdf9; border-color: #d4efe5; }
.strategy-ready.state-warning { background: var(--color-warning-soft); }
.strategy-ready.state-blocked { background: var(--color-danger-soft); }
h2, p { margin: 0; }
h2 { color: var(--text-primary); font-size: 16px; line-height: 22px; }
.state-ready h2 { color: var(--color-success); }
.state-warning h2 { color: var(--color-warning); }
.state-blocked h2 { color: var(--color-danger); }
.readiness-checks { display: flex; flex-wrap: wrap; gap: 6px 12px; margin: 0; padding: 0; list-style: none; color: var(--text-secondary); font-size: 12px; }
.readiness-checks li { display: flex; gap: 5px; align-items: center; }
.readiness-checks span { display: grid; place-items: center; flex: 0 0 14px; height: 14px; border-radius: 50%; background: var(--color-warning-soft); color: var(--color-warning); font-size: 10px; font-weight: 700; }
.readiness-checks .passed span { background: var(--color-success); color: #fff; }
.helper, .error { font-size: 12px; line-height: 1.6; overflow-wrap: anywhere; color: var(--text-muted); }
.error { color: var(--color-danger); }
</style>
