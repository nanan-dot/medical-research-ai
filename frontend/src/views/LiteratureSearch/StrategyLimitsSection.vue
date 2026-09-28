<script setup lang="ts">
import { computed } from "vue";
import BaseIcon from "../../components/ui/BaseIcon.vue";

import type { SearchStrategyDraft } from "../../types/searchStrategy";

const props = defineProps<{ strategy: SearchStrategyDraft }>();
const emit = defineEmits<{ edit: [] }>();

const limitEntries = computed(() => {
  const limits = props.strategy.limits;
  const candidates = [
    ["日期范围", limits.date_range],
    ["研究类型", limits.study_types],
    ["语言", limits.language],
    ["全文", limits.full_text],
  ] as const;
  return candidates
    .filter(([, value]) => Array.isArray(value) ? value.length > 0 : Boolean(value))
    .map(([label, value]) => ({ label, value: Array.isArray(value) ? value.join("、") : String(value) }));
});
</script>

<template>
  <section
    class="strategy-limits"
    aria-labelledby="strategy-limits-title"
  >
    <div class="limit-title"><h2 id="strategy-limits-title">已设置 {{ limitEntries.length }} 项限制</h2></div>
    <ul v-if="limitEntries.length">
      <li
        v-for="entry in limitEntries"
        :key="entry.label"
      >
        <BaseIcon name="document" /><span :title="entry.label">{{ entry.value }}</span>
      </li>
    </ul>
    <button
      type="button"
      class="limit-action"
      @click="emit('edit')"
    >
      查看 / 编辑
    </button><p
      v-if="!limitEntries.length"
      class="empty"
    >
      当前策略未设置额外限制，将按 PubMed 默认范围执行。
    </p>
  </section>
</template>

<style scoped>
.strategy-limits { min-width: 0; display: grid; grid-template-columns: minmax(0, 1fr) auto; align-content: center; gap: 8px 12px; padding: 12px 20px; border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--surface); box-shadow: var(--shadow-sm); }
.limit-title h2, .empty { margin: 0; }
.limit-title h2 { font-size: 16px; line-height: 22px; }
ul { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 6px 12px; margin: 0; padding: 0; list-style: none; }
li { display: flex; min-width: 0; gap: 5px; color: var(--text-secondary); font-size: 12px; }
li strong { color: var(--text-primary); flex-shrink: 0; }
li .icon { width: 15px; height: 15px; flex-shrink: 0; color: var(--text-secondary); }
li span { overflow-wrap: anywhere; }
.limit-action { grid-column: 2; grid-row: 1; border: 0; background: transparent; color: var(--color-primary); font: inherit; font-size: 12px; font-weight: 700; cursor: pointer; }
.limit-action:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
.empty { grid-column: 1 / -1; color: var(--text-muted); font-size: 12px; }
</style>
