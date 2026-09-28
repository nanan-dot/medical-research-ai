<script setup lang="ts">
import { computed } from "vue";

import type { SearchStrategyVersion, StrategyVersionComparison } from "../../types/searchStrategy";

const props = defineProps<{
  versions: SearchStrategyVersion[];
  comparison: StrategyVersionComparison | null;
  loading: boolean;
  error: string | null;
}>();

const emit = defineEmits<{
  createVersion: [];
  compare: [fromVersion: number, toVersion: number];
}>();

const comparisonPair = computed(() => props.versions.length >= 2
  ? [props.versions[1].version, props.versions[0].version] as const
  : null);

function compareLatest(): void {
  if (comparisonPair.value === null) return;
  emit("compare", comparisonPair.value[0], comparisonPair.value[1]);
}
</script>

<template>
  <section
    class="strategy-version-panel"
    aria-labelledby="strategy-version-title"
  >
    <div class="panel-header">
      <div>
        <h2 id="strategy-version-title">策略版本</h2>
        <p>版本保存的是策略快照，不会替代检索结果版本。</p>
      </div>
      <button
        type="button"
        :disabled="props.loading"
        @click="emit('createVersion')"
      >
        保存当前版本
      </button>
    </div>

    <p
      v-if="props.versions.length === 0"
      class="muted"
    >
      尚未保存策略版本。
    </p>
    <ol
      v-else
      class="version-list"
    >
      <li
        v-for="version in props.versions"
        :key="version.id"
      >
        <strong>策略版本 {{ version.version }}</strong>
        <span>{{ new Date(version.created_at).toLocaleString() }}</span>
      </li>
    </ol>

    <button
      v-if="comparisonPair"
      class="compare-button"
      type="button"
      :disabled="props.loading"
      @click="compareLatest"
    >
      比较最近两个版本
    </button>

    <dl
      v-if="props.comparison"
      class="comparison"
    >
      <div
        v-for="(_change, field) in props.comparison.changes"
        :key="field"
      >
        <dt>{{ field }}</dt>
        <dd>已变更</dd>
      </div>
    </dl>
    <p
      v-if="props.error"
      class="error"
      role="alert"
    >
      {{ props.error }}
    </p>
  </section>
</template>

<style scoped>
.strategy-version-panel { display: grid; gap: 12px; padding: 20px; border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--surface); }
.panel-header { display: flex; align-items: start; justify-content: space-between; gap: 12px; }.panel-header h2,.panel-header p { margin: 0; }.panel-header h2 { color: var(--text-primary); font-size: 1rem; }.panel-header p,.muted,.version-list span { color: var(--text-muted); font-size: .82rem; }
button { min-height: 36px; padding: 6px 10px; border: 1px solid var(--border-strong); border-radius: 6px; background: var(--surface); color: var(--color-primary); font: inherit; font-weight: 700; cursor: pointer; } button:disabled { cursor: wait; opacity: .55; } button:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
.version-list { display: grid; gap: 6px; margin: 0; padding: 0; list-style: none; }.version-list li { display: flex; justify-content: space-between; gap: 12px; padding: 8px 10px; background: var(--surface-muted); }.comparison { display: grid; gap: 6px; margin: 0; }.comparison div { display: flex; justify-content: space-between; gap: 12px; }.comparison dt,.comparison dd { margin: 0; }.error { margin: 0; color: var(--color-danger); }
@media (max-width: 640px) { .panel-header,.version-list li { flex-direction: column; }.panel-header button { width: 100%; } }
</style>
