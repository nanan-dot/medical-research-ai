<script setup lang="ts">
import { shallowRef } from "vue";

import type { SearchStrategyTerm } from "../../types/searchStrategy";

const props = defineProps<{
  terms: SearchStrategyTerm[];
  loading: boolean;
  error: string | null;
}>();

const emit = defineEmits<{
  add: [payload: { text: string; conceptGroup: string }];
  lock: [termId: number, isLocked: boolean];
  remove: [termId: number];
  remap: [];
}>();

const text = shallowRef("");
const conceptGroup = shallowRef("custom");

function addTerm(): void {
  const normalizedText = text.value.trim();
  if (!normalizedText) return;
  emit("add", { text: normalizedText, conceptGroup: conceptGroup.value });
  text.value = "";
}
</script>

<template>
  <section
    class="strategy-terms-panel"
    aria-labelledby="strategy-terms-title"
  >
    <div class="panel-header">
      <div>
        <h2 id="strategy-terms-title">检索术语</h2>
        <p>锁定术语会在重新映射时保留。</p>
      </div>
      <button
        type="button"
        :disabled="props.loading"
        @click="emit('remap')"
      >
        重新映射
      </button>
    </div>

    <form
      class="term-form"
      @submit.prevent="addTerm"
    >
      <label>
        术语
        <input
          v-model="text"
          :disabled="props.loading"
          maxlength="300"
          required
        >
      </label>
      <label>
        分组
        <input
          v-model="conceptGroup"
          :disabled="props.loading"
          maxlength="80"
          required
        >
      </label>
      <button
        type="submit"
        :disabled="props.loading || !text.trim()"
      >
        添加术语
      </button>
    </form>

    <ul
      v-if="props.terms.length"
      class="term-list"
    >
      <li
        v-for="term in props.terms"
        :key="term.id"
      >
        <div>
          <strong>{{ term.text }}</strong>
          <span>{{ term.concept_group }} · {{ term.source }}</span>
        </div>
        <div class="term-actions">
          <button
            type="button"
            :disabled="props.loading"
            @click="emit('lock', term.id, !term.is_locked)"
          >
            {{ term.is_locked ? "解锁" : "锁定" }}
          </button>
          <button
            type="button"
            :disabled="props.loading"
            :aria-label="`删除术语 ${term.text}`"
            @click="emit('remove', term.id)"
          >
            删除
          </button>
        </div>
      </li>
    </ul>
    <p
      v-else
      class="muted"
    >
      暂无术语；可手动添加，或从入口页重新生成策略。
    </p>
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
.strategy-terms-panel { display: grid; gap: 12px; padding: 20px; border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--surface); }
.panel-header,.term-list li,.term-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; }.panel-header h2,.panel-header p { margin: 0; }.panel-header h2 { color: var(--text-primary); font-size: 1rem; }.panel-header p,.term-list span,.muted { color: var(--text-muted); font-size: .82rem; }
.term-form { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) auto; gap: 8px; }.term-form label { display: grid; gap: 4px; color: var(--text-secondary); font-size: .8rem; }.term-form input { min-width: 0; min-height: 36px; border: 1px solid var(--border-strong); border-radius: 6px; padding: 6px 8px; font: inherit; }
button { min-height: 36px; padding: 6px 10px; border: 1px solid var(--border-strong); border-radius: 6px; background: var(--surface); color: var(--color-primary); font: inherit; font-weight: 700; cursor: pointer; } button:disabled { cursor: wait; opacity: .55; } button:focus-visible,input:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
.term-list { display: grid; gap: 6px; margin: 0; padding: 0; list-style: none; }.term-list li { padding: 8px 10px; background: var(--surface-muted); }.term-list li > div:first-child { display: grid; gap: 2px; }.error { margin: 0; color: var(--color-danger); }
@media (max-width: 640px) { .panel-header,.term-form,.term-list li { align-items: stretch; grid-template-columns: 1fr; flex-direction: column; }.term-form button { width: 100%; }.term-actions { width: 100%; }.term-actions button { flex: 1; } }
</style>
